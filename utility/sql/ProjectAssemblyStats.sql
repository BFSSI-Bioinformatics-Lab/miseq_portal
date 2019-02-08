-- Query for retrieving assembly metrics for a particular project

select
	m.sample_id, m.sample_name,ad.total_length, ad.num_contigs, s."top_taxName", m.fwd_reads, m.rev_reads, ad.assembly
from
	miseq_viewer_sample m,
	miseq_viewer_project p,
	analysis_sendsketchresult s,
	miseq_viewer_sampleassemblydata ad
where
	m.id = s.sample_id_id and
	p.id = m.project_id_id and
	ad.sample_id_id = s.sample_id_id and
	p.project_id = 'Listeria2016WGS';
