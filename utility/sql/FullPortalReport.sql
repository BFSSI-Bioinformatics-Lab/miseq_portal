-- Query for a general overview of all the samples in the portal

select
	m.sample_id, m.sample_name, p.project_id, r.run_id, ad.total_length, ad.num_contigs, ad.n50, ad.num_predicted_genes, s."top_taxName", m.fwd_reads, m.rev_reads
from
	miseq_viewer_sample m
left outer join analysis_sendsketchresult s on m.id = s.sample_id_id
left outer join miseq_viewer_project p on m.project_id_id = p.id
left outer join miseq_viewer_run r on m.run_id_id = r.id
left outer join miseq_viewer_sampleassemblydata ad on m.id = ad.sample_id_id;
