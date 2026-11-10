TOOL_LIST = {
        'SendSketch': {"title": 'SendSketch', "description": """Sendsketch compares query sketches to reference sketches hosted on a remote server via the Internet.
        Uses the R1 and R2 reads of any given sample and compares against a sketch of RefSeq.""", "link": "https://sourceforge.net/projects/bbmap/", "link_text": "BBMap"},
        'MobRecon': {"title": 'MobRecon', "description": """This tool reconstructs individual plasmid sequences from draft genome assemblies using
          the clustered plasmid reference databases provided by MOB-cluster.
          Provides in silico predictions of the replicon family, relaxase type, mate-pair
          formation type and predicted transferability of the plasmid.""", "link": "https://github.com/phac-nml/mob-suite", "link_text": "MOB-Suite"},
        'RGI': {"title": 'RGI', "description": """This application is used to predict resistome(s) from protein or nucleotide data based on
          homology and SNP models. The application uses reference data from the Comprehensive Antibiotic Resistance Database (CARD).""", "link": "https://github.com/ARPC-DL/RGI", "link_text": "RGI"},
        'Confindr': {"title": 'Confindr', "description": """ConFindr works by looking at conserved core genes - either using rMLST genes
        (53 genes are known to be single copy and conserved across all bacteria with some known exceptions, which ConFindr handles), 
        or custom sets of genes derived from core-genome schemes. As the genes ConFindr looks at are single copy, 
        any sample that has multiple alleles of one or more gene is likely to be contaminated.""", "link": "https://olc-bioinformatics.github.io/ConFindr/", "link_text": "ConFindr"},
        'rMLST': {"title": 'rMLST', "description": """Ribosomal Multilocus Sequence Typing (rMLST) is an approach that indexes variation 
        of the 53 genes encoding the bacterial ribosome protein subunits (rps genes) as a means of integrating microbial taxonomy and typing.""", "link": "https://pubmlst.org/species-id", "link_text": "PubMLST"},
        'Stx': {"title": 'Stx', "description": """StxSubtyper is a nextflow pipeline for subtyping Shiga toxin-producing E. coli strains 
        based on the identification of stx1 and stx2 gene variants.""", "link": "https://github.com/jashay90/nf-stxsubtyper", "link_text": "HC-stx-subtyper"},
        'SalTy': {"title": 'SalTy', "description": """SalTy is a nextflow pipeline to run various analysis tools on a Salmonella genome, 
        and to generate a summary XLSX report. Based on a pipeline by Annika Flint.""", "link": "https://github.com/jashay90/nf-salmonella", "link_text": "Salmonella Nextflow Pipeline"}
}