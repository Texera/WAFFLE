"""Fetch the pinned official KNIME examples; reject a changed upstream archive."""
import argparse,hashlib,json,urllib.request,zipfile
from pathlib import Path

def download(out):
    spec=json.loads(Path(__file__).with_name('sources.json').read_text(encoding='utf-8'))
    out.mkdir(parents=True,exist_ok=False);originals=out/'originals';originals.mkdir()
    for item in [*spec['cases'],spec['writer_template']]:
        name=item['path'].split('/')[-1]
        data=urllib.request.urlopen('https://api.hub.knime.com/repository/'+item['id']+':data',timeout=60).read()
        assert hashlib.sha256(data).hexdigest()==item['archive_sha256'],f'Upstream archive changed: {name}'
        archive=out/(name+'.knwf');archive.write_bytes(data)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():assert (originals/member.filename).resolve().is_relative_to(originals.resolve())
            z.extractall(originals)
    (out/'selection.json').write_text(json.dumps(dict(criterion=spec['criterion'],items=spec['cases']),indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args();download(a.output)
