import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

# logger = logging.getLogger('raven')
logger = logging.getLogger(__name__)


@method_decorator(staff_member_required, name='dispatch')
class SampleWorkbookIndexView(LoginRequiredMixin, TemplateView):
    template_name = 'sample_workbooks/sample_workbooks_index.html'


sample_workbook_index_view = SampleWorkbookIndexView.as_view()
