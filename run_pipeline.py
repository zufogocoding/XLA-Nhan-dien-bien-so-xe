"""Run the local end-to-end image pipeline and persist its result."""

import argparse
import json
from pathlib import Path
import shutil
import sys
import uuid

from src.service import RecognitionService


if __name__=='__main__':
    # Windows redirected stdout can default to cp1252, which cannot encode provinces.
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('image',type=Path)
    parser.add_argument('--vehicle-type',choices=('unknown','car','motorcycle'),default='unknown')
    parser.add_argument('--runtime',type=Path,default=Path('outputs/runtime'))
    args=parser.parse_args()
    if not args.image.is_file():
        parser.error('input image does not exist')
    service=RecognitionService(args.runtime)
    target=service.public/'uploads'/(uuid.uuid4().hex+args.image.suffix.lower())
    shutil.copyfile(args.image,target)
    print(json.dumps(service.process_image(target,vehicle_type=args.vehicle_type),ensure_ascii=False,indent=2))
