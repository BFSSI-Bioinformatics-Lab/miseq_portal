"""
Get rMLST profile(s) via the pubmlst API, and process the result
adapted from the script written by Keith Jolley

"""

import requests, base64, logging, json
from pathlib import Path

logger = logging.getLogger('raven')


def query_rmlst(assembly: Path, outdir: Path) -> Path:
    uri = 'http://rest.pubmlst.org/db/pubmlst_rmlst_seqdef_kiosk/schemes/1/sequence'
    logger.info(f"Submitting rMLST query for {assembly}")
    with open(assembly, 'r') as x:
        fasta = x.read()
    payload = '{"base64":true,"details":true,"sequence":"' + base64.b64encode(fasta.encode()).decode() + '"}'
    response = requests.post(uri, data=payload)
    if response.status_code == requests.codes.ok:
        data = response.json()
        jout = outdir / 'rmlst.json'
        with open(jout , 'w') as w:
            json.dump(data, w)
        return jout
        # try:
        #     data['taxon_prediction']
        # except KeyError:
        #     print("No match")
        #     sys.exit(0)
        # for match in data['taxon_prediction']:
        #     print("Rank: " + match['rank'])
        #     print("Taxon:" + match['taxon'])
        #     print("Support:" + str(match['support']) + "%")
        #     print("Taxonomy" + match['taxonomy'] + "\n")

    else:
        logging.info("Could not perform rMLST analysis: {response.text}")

