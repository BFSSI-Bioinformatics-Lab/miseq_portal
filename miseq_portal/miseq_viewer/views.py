import json
import logging
from pathlib import Path
import xlsxwriter
import io
import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.views.generic import DetailView, ListView
from rest_framework import viewsets
from django.http import HttpResponse

from config.settings.base import MEDIA_ROOT
from miseq_portal.analysis.models import AnalysisSample
from miseq_portal.miseq_uploader import parse_samplesheet
from miseq_portal.miseq_uploader.parse_interop import get_qscore_json
from miseq_portal.miseq_viewer.models import Project, Run, Sample, UserProjectRelationship, SampleAssemblyData, \
    MergedSampleComponent, SampleLogData, RunSamplesheet, SampleSheetSampleData
from miseq_portal.minion_viewer.models import MinIONSample
from miseq_portal.miseq_viewer.serializers import SampleSerializer, RunSerializer, ProjectSerializer

logger = logging.getLogger('django')


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    context_object_name = 'project_list'
    template_name = "miseq_viewer/project_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['overview_json'] = self.get_overview_data()

        context['sample_count_dict'] = {project.project_id: (len(Sample.objects.filter(project_id_id=project)) +
                                                             len(MinIONSample.objects.filter(project_id_id=project)))
                                        for project in Project.objects.all()}
        return context

    @staticmethod
    def get_overview_data():
        overview_dict = dict()
        overview_dict['number_of_projects'] = len(Project.objects.all())
        overview_dict['number_of_samples'] = len(Sample.objects.all()) + len(MinIONSample.objects.all())
        overview_dict['number_of_runs'] = len(Run.objects.all())
        return json.dumps(overview_dict)

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = Project.objects.all().order_by('project_id')
        else:
            valid_projects = UserProjectRelationship.objects.filter(user_id=self.request.user)
            valid_projects = [p.project_id for p in valid_projects]
            queryset = Project.objects.filter(Q(project_id__in=valid_projects)).order_by('project_id')
        return queryset


project_list_view = ProjectListView.as_view()


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    context_object_name = 'project'
    template_name = "miseq_viewer/project_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['run_list'] = Run.objects.all()
        # for some reason, projects with no MiSeq samples do not have a context['project'], but everything seems to work with context['object']
        context['sample_list'] = Sample.objects.filter(project_id=context['object'], hide_flag=False)
        context['minion_sample_list'] = MinIONSample.objects.filter(project_id=context['object'])

        # Filter out samples that are missing data for the project_detail.html template
        context['has_sample_log_data'] = context['sample_list'].filter(samplelogdata__isnull=False)
        context['has_mash_result'] = context['sample_list'].filter(mashresult__isnull=False)

        return context


project_detail_view = ProjectDetailView.as_view()


class RunListView(LoginRequiredMixin, ListView):
    model = Run
    context_object_name = 'run_list'
    template_name = "miseq_viewer/run_list.html"


run_list_view = RunListView.as_view()


class RunDetailView(LoginRequiredMixin, DetailView):
    model = Run
    context_object_name = 'run'
    template_name = "miseq_viewer/run_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['interop_data_avaiable'] = True

        # Get run folder to feed to the interop parser
        try:
            run = context['run']
        except KeyError:
            run = context['object']

        interop_folder = run.get_interop_directory()

        if interop_folder is None:
            logger.info("WARNING: The InterOp directory for this run is not stored in the database")
            context['interop_data_avaiable'] = False

        # Grab Samplesheet path
        samplesheet = Path(MEDIA_ROOT) / str(run.sample_sheet)

        # Try to receive InterOp data, if it's not available then display an alert on miseq_viewer/run_detail.html
        try:
            context['qscore_json'] = get_qscore_json(Path(MEDIA_ROOT) / interop_folder.parent)
        except Exception as e:
            # logging.debug(f'TRACEBACK: {e}')
            context['interop_data_avaiable'] = False

        # logger.debug(f"interop_data_available: {context['interop_data_avaiable']}")
        context['sample_list'] = Sample.objects.filter(run_id=run, hide_flag=False)
        context['samplesheet_headers'] = RunSamplesheet.objects.get(run_id=run)
        context['samplesheet_df'] = parse_samplesheet.read_samplesheet_to_html(sample_sheet=samplesheet)

        return context


run_detail_view = RunDetailView.as_view()


def qaqc_excel(request):
    # I am building off of this: https://xlsxwriter.readthedocs.io/example_django_simple.html
    if request.method == 'POST':
        sample_list = request.POST.get('sample_list')[:-1].split(",")
        columns = ["sample_id", "sample_name", "project_id", "run_id"]
        assemblycolumns = [["i5_index_id", "samplesheet", "str"], ["i7_index_id", "samplesheet", "str"],
                           ["index", "samplesheet", "str"], ["index2", "samplesheet", "str"],
                           ["sample_plate", "samplesheet", "str"], ["sample_well", "samplesheet", "str"],
                           ["total_length", "assembly", "str"], ["mean_coverage", "assembly", "str"],
                           ["num_contigs", "assembly", "str"], ["n50", "assembly", "str"],
                           ["num_predicted_genes", "assembly", "str"], ["description", "samplesheet", "str"],
                           ["top_hit", "mash", "str"], ["fwd_reads", "sample", "path"], ["rev_reads", "sample", "path"],
                           ["assembly", "assembly", "path"], ["created", "sample", "date"]]
        confindrcolumns = ["contam_status",  "percent_contam", "percent_contam_std_dev",
                           "num_contam_snvs", "genus", "bases_examined"]

        # Create an in-memory output file for the new workbook.
        output = io.BytesIO()

        workbook = xlsxwriter.Workbook(output)
        assemblysheet = workbook.add_worksheet("Portal Report")
        confindrsheet = workbook.add_worksheet("Confindr Report")
        combinedsheet = workbook.add_worksheet("Combined")
        # write headers
        for s in (assemblysheet, confindrsheet, combinedsheet):
            for colnum, column in enumerate(columns):
                s.write(0, colnum, column)
        for s in (assemblysheet, combinedsheet):
            for colnum, column in enumerate(assemblycolumns):
                s.write(0, colnum + len(columns), column[0])
        for colnum, column in enumerate(confindrcolumns):
            confindrsheet.write(0, colnum + len(columns), column)
            combinedsheet.write(0, colnum + len(columns) + len(assemblycolumns), column)
        rowcount = 0
        for sample in sample_list:
            rowcount += 1
            sample_object = Sample.objects.get(id=sample)
            # fields common to all 3 tables
            # grab run_id and project_id once
            try:
                run_id = Run.objects.get(id=sample_object.run_id_id).run_id
            except:
                run_id = "NA"
            try:
                project_id = Project.objects.get(id=sample_object.project_id_id).project_id
            except:
                project_id = "NA"
            for s in (assemblysheet, confindrsheet, combinedsheet):
                for i in range(0, 2):
                    s.write(rowcount, i, getattr(sample_object, columns[i]))
                s.write(rowcount, 2, project_id)
                s.write(rowcount, 3, run_id)
            # fields in assembly sheet
            # first, try to get all the necessary objects
            try:
                samplesheet_object = SampleSheetSampleData.objects.get(sample_id_id=sample_object.id)
            except:
                samplesheet_object = None
            try:
                assembly_object = SampleAssemblyData.objects.get(sample_id=sample_object.id)
            except:
                assembly_object = None
            try:
                mashresult = sample_object.mashresult.top_hit
            except:
                # Get top Sendsketch hit if it exists
                try:
                    mashresult = sample_object.sendsketchresult.top_taxName
                except:
                    mashresult = "NA"
            # once you have all the necessary objects, iterate through the fields
            for colnum, column in enumerate(assemblycolumns):
                if column[1] == "sample":
                    towrite = getattr(sample_object, column[0])
                elif column[1] == "samplesheet":
                    if samplesheet_object != None:
                        towrite = getattr(samplesheet_object, column[0])
                    else:
                        towrite = "NA"
                elif column[1] == "assembly":
                    if assembly_object != None:
                        towrite = getattr(assembly_object, column[0])
                    else:
                        towrite = "NA"
                elif column[1] == "mash":
                    towrite = mashresult
                else:
                    towrite = "Something went wrong"
                if towrite != "NA":
                    if column[2] == "path":
                        try:
                            towrite = towrite.path
                        except:
                            towrite = "NA"
                    elif column[2] == "date":
                        try:
                            towrite = towrite.strftime('%Y-%m-%d')
                        except:
                            towrite = "NA"
                assemblysheet.write(rowcount, colnum + len(columns), towrite)
                combinedsheet.write(rowcount, colnum + len(columns), towrite)

            # confindr fields
            for colnum, column in enumerate(confindrcolumns):
                confindrsheet.write(0, colnum + len(columns), column)
                combinedsheet.write(0, colnum + len(columns) + len(assemblycolumns), column)
            try:
                confindr_object = sample_object.confindrresultassembly
                for i in range(0, len(confindrcolumns)):
                    towrite = getattr(confindr_object, confindrcolumns[i])
                    if towrite != towrite:  # this is a check for NaN
                        towrite = "ND"
                    confindrsheet.write(rowcount, i + len(columns), towrite)
                    combinedsheet.write(rowcount, i + len(columns) + len(assemblycolumns), towrite)
            except:
                for i in range(0, len(confindrcolumns)):
                    confindrsheet.write(rowcount, i + len(columns), "NA")
                    combinedsheet.write(rowcount, i + len(columns) + len(assemblycolumns), "NA")


        # Close the workbook before sending the data.
        workbook.close()

        # Rewind the buffer.
        output.seek(0)

        # Set up the Http response.
        response = HttpResponse(
            output,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = "attachment; filename=qaqc_report.xlsx"
        return response
    else:
        return None


class SampleDetailView(LoginRequiredMixin, DetailView):
    model = Sample
    context_object_name = 'sample'
    template_name = "miseq_viewer/sample_detail.html"

    def get_queryset(self):
        """ This ensures hidden samples do not appear """
        qs = super(SampleDetailView, self).get_queryset()
        return qs.filter(hide_flag=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sample_object = context['sample']

        # Query the AnalysisSample model to see if there are any analyses associated with this sample for this user
        analysis_samples = AnalysisSample.objects.filter(sample_id=context['sample'], user_id=self.request.user)

        # Get assembly data if it exists
        try:
            context['assembly_data'] = SampleAssemblyData.objects.get(sample_id=context['sample'])
        except SampleAssemblyData.DoesNotExist:
            context['assembly_data'] = None

        # Get Mash hit if it exists
        try:
            context['top_refseq_hit'] = sample_object.mashresult.top_hit
        except:
            # Get top Sendsketch hit if it exists
            try:
                context['top_refseq_hit'] = SampleAssemblyData.objects.get(
                    sample_id=context['sample']).sample_id.sendsketchresult.top_taxName
            except:
                context['top_refseq_hit'] = None

        # Get confindr results
        try:
            context['confindr_result'] = sample_object.confindrresultassembly
        except:
            context['confindr_result'] = None

        # Set to None if the FileField for the assembly is empty
        try:
            if str(context['assembly_data'].assembly) == '':
                context['assembly_data'] = None
        except AttributeError:
            context['assembly_data'] = None

        if len(analysis_samples) > 0:
            context['analysis_samples'] = analysis_samples
        else:
            context['analysis_samples'] = None

        # Get associated samples if sample type is MER
        if context['sample'].sample_type == 'MER':
            merged_number_reads = 0
            merged_sample_yield = 0
            components = MergedSampleComponent.objects.filter(group_id=context['sample'].component_group)
            sample_components = []

            # Get corresponding Sample objects
            merged_sample_yield_broken_flag = False
            merged_number_reads_broken_flag = False
            for component in components:
                sample_component = Sample.objects.get(sample_id=component.component_id)
                sample_components.append(sample_component)

                # Try to access samplelogdata from Sample, if it's missing continue to the next sample
                try:
                    samplelogdata = sample_component.samplelogdata
                except ObjectDoesNotExist:
                    merged_number_reads_broken_flag = True
                    merged_sample_yield_broken_flag = True
                    continue

                # If one of the components is missing data, display N/A for merged value on page
                if samplelogdata.number_reads is None:
                    merged_number_reads_broken_flag = True
                if samplelogdata.sample_yield is None:
                    merged_sample_yield_broken_flag = True

                if merged_sample_yield_broken_flag or merged_number_reads_broken_flag:
                    continue
                else:
                    # Sum up total number of reads across each sample_component if none of them have N/A values
                    merged_number_reads += samplelogdata.number_reads
                    merged_sample_yield += samplelogdata.sample_yield / 1000000

            context['sample_components'] = sample_components

            # TODO: Refactor this logic into a property for a Sample object in models.py?
            # The summed values for each component for number_reads and sample_yield, respectively
            if merged_number_reads_broken_flag:
                context['merged_number_reads'] = "N/A"
            else:
                context['merged_number_reads'] = merged_number_reads
            if merged_sample_yield_broken_flag:
                context['merged_sample_yield'] = "N/A"
            else:
                context['merged_sample_yield'] = merged_sample_yield

        # Check if sample is part of a MER sample
        merged_sample_references = []
        if context['sample'].sample_type == 'BMH':
            component_query = MergedSampleComponent.objects.filter(component_id=context['sample'])
            if len(component_query) > 0:
                for component in component_query:
                    try:
                        merged_sample_reference = Sample.objects.get(component_group=component.group_id)
                        merged_sample_references.append(merged_sample_reference)
                    except Sample.DoesNotExist:
                        pass
        context['merged_sample_references'] = merged_sample_references

        # Check if sample has a related samplelogdata object
        try:
            SampleLogData.objects.get(sample_id=context['sample'])
            context['has_sample_log_data'] = True
        except SampleLogData.DoesNotExist:
            context['has_sample_log_data'] = False

        # Get user's browser details to determine whether or not to show the disclaimer RE: downloading .fastq.gz
        if "firefox" in self.request.META['HTTP_USER_AGENT'].lower():
            context['browser_flag'] = True
        else:
            context['browser_flag'] = False

        return context


sample_detail_view = SampleDetailView.as_view()


# django-rest-framework
class SampleViewSet(viewsets.ModelViewSet):
    serializer_class = SampleSerializer

    def get_queryset(self):
        # Staff get the full queryset, otherwise only show samples that are in projects user has rights to
        if self.request.user.is_staff:
            queryset = Sample.objects.all().order_by('sample_id')
        else:
            valid_projects = UserProjectRelationship.objects.filter(user_id=self.request.user)
            valid_projects = [p.project_id for p in valid_projects]
            queryset = Sample.objects.filter(Q(hide_flag=False) &
                                             Q(project_id__in=valid_projects)
                                             ).order_by('sample_id')
        return queryset


class RunViewSet(viewsets.ModelViewSet):
    queryset = Run.objects.all().order_by('run_id')
    serializer_class = RunSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = Project.objects.all().order_by('project_id')
        else:
            valid_projects = UserProjectRelationship.objects.filter(user_id=self.request.user)
            valid_projects = [p.project_id for p in valid_projects]
            queryset = Project.objects.filter(Q(project_id__in=valid_projects)).order_by('project_id')
        return queryset
