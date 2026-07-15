"""
Get rMLST profile(s) via the pubmlst API, and process the result
adapted from the script written by Keith Jolley

"""

import requests, base64, logging, json
from pathlib import Path

logger = logging.getLogger('raven')


def query_rmlst(assembly: Path, outdir: Path, root: Path):
    uri = 'https://rest.pubmlst.org/db/pubmlst_rmlst_seqdef_kiosk/schemes/1/sequence'
    logger.info(f"Submitting rMLST query for {assembly}")
    with open(assembly, 'r') as x:
        fasta = x.read()
    payload = '{"base64":true,"details":true,"sequence":"' + base64.b64encode(fasta.encode()).decode() + '"}'
    response = requests.post(uri, data=payload)
    if response.status_code == requests.codes.ok:
        data = response.json()
        jout = outdir / 'rmlst.json'
        with open(root / jout , 'w') as w:
            json.dump(data, w)
        try:
            support = data['taxon_prediction'][0]['support']
            taxon = data['taxon_prediction'][0]['taxon']
        except KeyError:
            support = None
            taxon = None
        try:
            rST = data['fields']['rST']
        except KeyError:
            rST = None

        csvout = outdir / 'rmlst.csv'
        with open(root / csvout, 'w') as w:
            w.write("Locus,Allele,Length,Contig,Start,End\n")
            try:
                for exact_match in data['exact_matches']:
                    em = data['exact_matches'][exact_match][0]
                    w.write(",".join(str(item) for item in [exact_match, em['allele_id'], em['length'], em['contig'], em['start'], em['end']]))
                    w.write("\n")
            except KeyError:
                csvout = None

        return {'json': str(jout), 'csv': str(csvout), 'support': support, 'taxon': taxon, 'rST': rST}

    else:
        logging.info(f"Could not perform rMLST analysis: {response.text}")
