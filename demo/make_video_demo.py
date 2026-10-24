"""Render actual sampled-frame API results over the approved source video.

This is an annotated inference demo, not a recording of webcam/web interactions.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image,ImageDraw,ImageFont

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.database import Database


def font(size: int, bold: bool = False):
    path=Path('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf')
    return ImageFont.truetype(str(path),size) if path.exists() else ImageFont.load_default(size=size)


def make_demo(video: Path, report: Path, runtime: Path, output: Path):
    result=json.loads(report.read_text(encoding='utf-8'))
    source=result['source_url'].removeprefix('/files/')
    db=Database(runtime/'plates.sqlite3')
    with db.connection() as connection:
        rows=connection.execute('SELECT * FROM plates WHERE image_path = ? ORDER BY id',(source,)).fetchall()
    records={}
    for row in rows:
        record=db.decode(row)
        if 'frame_index' in record['metadata']:
            records[record['metadata']['frame_index']]=record
    if not records:
        raise ValueError('No persisted sampled-frame results; process the video through the API first.')
    capture=cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise ValueError('cannot read source video')
    fps=float(capture.get(cv2.CAP_PROP_FPS))
    width,height=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total=int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    canvas_width=width+352
    canvas_height=max(600,height+120)
    canvas_width+=canvas_width%2; canvas_height+=canvas_height%2
    output.parent.mkdir(parents=True,exist_ok=True)
    writer=imageio_ffmpeg.write_frames(str(output),(canvas_width,canvas_height),fps=fps,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',quality=7,macro_block_size=2,ffmpeg_log_level='error')
    writer.send(None)
    index=0
    last=None
    try:
        while True:
            ok,frame=capture.read()
            if not ok:
                break
            if index in records:
                last=records[index]
            canvas=Image.new('RGB',(canvas_width,canvas_height),'#f2f5ec')
            canvas.paste(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)),(0,60))
            draw=ImageDraw.Draw(canvas)
            draw.rectangle((0,0,canvas_width,59),fill='#153d38')
            draw.text((22,16),'BIỂN SỐ LAB  |  Demo kết quả xử lý video',font=font(23,True),fill='white')
            draw.text((width+22,80),'KẾT QUẢ KHUNG HÌNH',font=font(16,True),fill='#1d4e42')
            draw.text((width+22,111),f'Frame {index}/{total-1} · lấy mẫu mỗi {result["stride"]} frame',font=font(13),fill='#718371')
            if last:
                bbox=last['metadata'].get('bbox')
                if bbox:
                    x1,y1,x2,y2=bbox
                    draw.rectangle((x1,y1+60,x2,y2+60),outline='#76efb2',width=3)
                text=last['plate_text'] or last['raw_text'] or 'Chưa đọc được'
                draw.text((width+22,155),text,font=font(27,True),fill='#1b5144')
                draw.text((width+22,200),'Trạng thái: '+last['status'],font=font(14),fill='#637765')
                if last['crop_path']:
                    crop=Image.open(runtime/'public'/last['crop_path']).convert('RGB')
                    crop.thumbnail((300,175))
                    canvas.paste(crop,(width+22,240))
                if last['confidence'] is not None:
                    draw.text((width+22,435),f'Điểm OCR trung bình: {last["confidence"]:.1%}',font=font(14),fill='#637765')
                vote=last['metadata'].get('temporal_vote',{})
                if vote.get('plate_text'):
                    draw.text((width+22,470),'Voting: '+vote['plate_text'],font=font(16,True),fill='#1b5144')
                draw.text((width+22,505),'Hiển thị kết quả của frame lấy mẫu gần nhất.',font=font(11),fill='#718371')
            draw.rectangle((0,canvas_height-41,canvas_width,canvas_height),fill='#153d38')
            draw.text((20,canvas_height-30),'Nguồn: winter2897 / test_1.mp4 · Dữ liệu thực, chưa có nhãn OCR video để đo accuracy.',font=font(13),fill='#dbe9db')
            draw.rectangle((0,canvas_height-46,round(canvas_width*(index+1)/max(1,total)),canvas_height-42),fill='#7cae75')
            writer.send(np.asarray(canvas).tobytes())
            index+=1
    finally:
        capture.release()
        writer.close()
    print(json.dumps({'output':str(output),'frames':index,'fps':fps,'sampled_records':len(records),'scope':'annotated actual inference results; no webcam or web recording'},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--video',type=Path,default=Path('data/external/winter2897/test_1.mp4'))
    parser.add_argument('--report',type=Path,default=Path('reports/local_video_smoke_test.json'))
    parser.add_argument('--runtime',type=Path,default=Path('outputs/runtime'))
    parser.add_argument('--output',type=Path,default=Path('demo/video_demo.mp4'))
    args=parser.parse_args()
    make_demo(args.video,args.report,args.runtime,args.output)
