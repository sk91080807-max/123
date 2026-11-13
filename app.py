"""말랑 네일: 버튼으로 고르는 단일 화면 앱.
설치: pip install -r requirements.txt
실행: streamlit run app.py
배포: GitHub에 app.py와 requirements.txt 업로드 후 Streamlit Community Cloud에서 app.py 배포.
QR 공유에 공개 배포 주소를 입력하세요. GitHub Pages로는 실행할 수 없습니다.
수동 사진 합성과 AI 추천 없이 색상/그림 선택, 디자인 PNG 저장, 앱 접속용 QR을 제공합니다.
"""
from io import BytesIO
import math
from urllib.parse import urlparse
import streamlit as st
import qrcode
import json
from PIL import Image, ImageDraw, ImageColor

PALETTE = {
    '밀키 핑크': '#F4B8CB', '라벤더': '#BFA8E5', '피치 코랄': '#F3AD99',
    '버터 옐로': '#F3DB8C', '민트': '#A5D8C3', '스카이 블루': '#9FC9E8',
    '로즈 베이지': '#C89698', '베리 핑크': '#CD527C', '밀크 화이트': '#F8F4EC',
}

def png_bytes(image):
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()

def nail_patch(color, pattern, width=100, height=160):
    """투명한 손톱 스티커. 자유 크기 변형과 회전 후 사진에 합성."""
    width, height = max(12, int(width)), max(20, int(height))
    mask = Image.new('L', (width, height), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((1, 1, width-2, height-2), radius=min(width//2, height//3), fill=255)
    patch = Image.new('RGBA', (width, height), color)
    d = ImageDraw.Draw(patch)
    white = '#FFF9FC'
    if pattern == '도트':
        r = max(2, width//22)
        for x in (width*.3, width*.7):
            for y in (height*.3, height*.5, height*.7):
                d.ellipse((x-r, y-r, x+r, y+r), fill=white)
    elif pattern == '하트':
        # 수학 곡선: 폰트나 외부 그림 파일 없이 하트를 그립니다.
        points = []
        for i in range(120):
            t = i*2*math.pi/120
            x = 16*math.sin(t)**3
            y = 13*math.cos(t)-5*math.cos(2*t)-2*math.cos(3*t)-math.cos(4*t)
            points.append((width*.5+x*width*.018, height*.5-y*width*.018))
        d.polygon(points, fill=white)
    elif pattern == '꽃':
        cx, cy, radius = width*.5, height*.5, width*.19
        r = width*.115
        for i in range(5):
            a = i*2*math.pi/5
            x, y = cx+radius*math.cos(a), cy+radius*math.sin(a)
            d.ellipse((x-r, y-r, x+r, y+r), fill=white)
        r = width*.09
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill='#F3DB8C')
    elif pattern in ('고양이', '강아지', '토끼'):
        # 기하 도형으로 만든 동물 그림: 별도 이미지나 API 키가 필요 없습니다.
        def ellipse(box, fill):
            d.ellipse(tuple(v * (width if j % 2 == 0 else height)
                            for j, v in enumerate(box)), fill=fill)
        ink = '#59415E'
        if pattern == '고양이':
            d.polygon([(width*.23, height*.48), (width*.22, height*.27),
                       (width*.47, height*.41)], fill=white)
            d.polygon([(width*.53, height*.41), (width*.78, height*.27),
                       (width*.77, height*.48)], fill=white)
        elif pattern == '토끼':
            ellipse((.27, .18, .45, .51), white)
            ellipse((.55, .18, .73, .51), white)
            ellipse((.32, .23, .40, .43), '#E9A5C4')
            ellipse((.60, .23, .68, .43), '#E9A5C4')
        else:
            ellipse((.12, .36, .35, .65), '#CBA687')
            ellipse((.65, .36, .88, .65), '#CBA687')
        ellipse((.23, .38, .77, .72), white)
        ellipse((.35, .50, .41, .55), ink)
        ellipse((.59, .50, .65, .55), ink)
        ellipse((.46, .58, .54, .62), '#C5789C')
        if pattern == '고양이':
            for yy in (.57, .62):
                d.line((width*.12, height*(yy-.02), width*.32, height*yy), fill=ink, width=max(1,width//60))
                d.line((width*.68, height*yy, width*.88, height*(yy-.02)), fill=ink, width=max(1,width//60))
    elif pattern == '프렌치':
        d.rectangle((0, 0, width, height*.2), fill=white)
    d.line((width*.23, height*.25, width*.23, height*.59), fill='#FFFFFF70', width=max(1, width//22))
    patch.putalpha(mask)
    return patch

def design_card(base, accent, pattern):
    canvas = Image.new('RGBA', (900, 380), '#FFF4FA')
    for i in range(5):
        color = PALETTE[accent if i == 3 else base]
        tile = nail_patch(color, pattern, 110, 205)
        canvas.alpha_composite(tile, (65+i*165, 75))
    return canvas.convert('RGB')

def valid_public_url(value):
    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()
    return (parsed.scheme == 'https' and bool(host) and '.' in host
            and host not in ('localhost', '127.0.0.1', '0.0.0.0')
            and not parsed.username and not parsed.password)

SHAPES = ['둥근형', '사각형', '둥근 사각형', '타원형', '아몬드형', '직접 입력']
PATTERNS = ['없음', '하트', '꽃', '도트', '프렌치', '고양이', '강아지', '토끼']

def pick_color(value):
    text = value.strip()
    aliases = {'핑크':'밀키 핑크','분홍':'밀키 핑크','보라':'라벤더','노랑':'버터 옐로','하늘':'스카이 블루','빨강':'red','검정':'black','흰색':'white','파랑':'blue','초록':'green','주황':'orange'}
    text = aliases.get(text, text)
    text = PALETTE.get(text, text)
    return ImageColor.getrgb(text)


def set_choice(key, value):
    st.session_state[key] = value


def preview(rgb, pattern, shape):
    canvas = Image.new('RGBA', (900, 340), '#FFF4FA')
    for i in range(5):
        tile = nail_patch(rgb, pattern, 108, 205)
        mask = Image.new('L', tile.size)
        draw = ImageDraw.Draw(mask)
        if shape in ('타원형', '아몬드형'):
            draw.ellipse((2, 2, 105, 202), fill=255)
        else:
            radius = {'사각형':8, '둥근 사각형':24}.get(shape, 50)
            draw.rounded_rectangle((2,2,105,202), radius=radius, fill=255)
        tile.putalpha(mask)
        canvas.alpha_composite(tile, (65+165*i, 65))
    return canvas.convert('RGB')


def validate_records(data):
    if not isinstance(data, list) or len(data)>100:
        raise ValueError('가족 기록은 최대 100개까지 불러올 수 있어요.')
    fields = ['이름','손톱 형태','색상','그림','메모']
    clean=[]
    for row in data:
        if not isinstance(row, dict) or any(not isinstance(row.get(k),str) for k in fields):
            raise ValueError('가족 기록 파일 형식이 맞지 않아요.')
        if not row['이름'].strip() or any(len(row[k])>500 for k in fields):
            raise ValueError('이름이 없거나 내용이 너무 길어요.')
        pick_color(row['색상'])
        if row['이름'].strip() in [r['이름'] for r in clean]:
            raise ValueError('같은 이름이 중복되어 있어요.')
        clean.append({k:row[k].strip() for k in fields})
    return clean


def main():
    st.set_page_config(page_title='우리 가족 네일',page_icon='💅',layout='wide')
    st.markdown('''<style>
    .stApp{background:#faf2ff;color:#392541;color-scheme:light;}
    .block-container{max-width:1150px;padding-top:3.5rem;padding-bottom:1rem;}
    h1{font-size:1.65rem!important;line-height:1.5!important;white-space:normal!important;}
    h1,h2,h3,p,label{color:#392541!important;}
    div.stButton>button,div.stDownloadButton>button,button[kind="secondary"],button[kind="primary"]{
      background:#fff!important;color:#392541!important;border:1px solid #9d73ad!important;
      border-radius:12px!important;min-height:40px;height:auto!important;padding:7px 9px!important;}
    div.stButton>button *,div.stDownloadButton>button *{color:#392541!important;white-space:normal!important;line-height:1.4!important;}
    div.stButton>button[kind="primary"]{background:#e8c6ed!important;border:2px solid #79508b!important;}
    div.stButton>button:hover,div.stDownloadButton>button:hover{background:#f0ddf6!important;}
    input,textarea,[data-baseweb="select"]>div{background:#fff!important;color:#392541!important;-webkit-text-fill-color:#392541!important;}
    [data-testid="stSelectbox"] span{color:#392541!important;}
    [data-testid="stVerticalBlock"]{gap:.55rem;}
    @media(max-width:700px){.block-container{padding-top:3rem;padding-left:1rem;padding-right:1rem;}}
    </style>''',unsafe_allow_html=True)
    defaults={'family_records':[],'name':'','shape_compact':'둥근형','color_compact':'밀키 핑크','pattern_compact':'하트','note_compact':''}
    for key,value in defaults.items():
        if key not in st.session_state:st.session_state[key]=value
    st.title('💅 우리 가족 네일')
    def load_record():
        name=st.session_state.member
        if name=='＋ 새 가족':
            for key,value in [('name',''),('shape_compact','둥근형'),('color_compact','밀키 핑크'),('pattern_compact','하트'),('note_compact','')]:
                st.session_state[key]=value
        else:
            row=next(r for r in st.session_state.family_records if r['이름']==name)
            for key,field in [('name','이름'),('shape_compact','손톱 형태'),('color_compact','색상'),('pattern_compact','그림'),('note_compact','메모')]:
                st.session_state[key]=row[field]
    left,right=st.columns([1.1,1],gap='large')
    with left:
        a,b=st.columns(2)
        a.selectbox('가족 선택',['＋ 새 가족']+[r['이름'] for r in st.session_state.family_records],key='member',on_change=load_record)
        b.text_input('이름',key='name',max_chars=40,placeholder='엄마')
        shape_options=SHAPES[:-1]
        if st.session_state.shape_compact not in shape_options:shape_options=shape_options+[st.session_state.shape_compact]
        st.selectbox('손톱 형태',shape_options,key='shape_compact')
        st.caption('색·그림은 목록에서 고르거나 새 값을 입력하세요.')
        color_options=list(PALETTE)
        if st.session_state.color_compact not in color_options:color_options.append(st.session_state.color_compact)
        st.selectbox('색 (예: 빨강, #FF99CC)',color_options,key='color_compact',accept_new_options=True)
        pattern_options=PATTERNS.copy()
        if st.session_state.pattern_compact not in pattern_options:pattern_options.append(st.session_state.pattern_compact)
        st.selectbox('그림 (직접 입력 가능)',pattern_options,key='pattern_compact',accept_new_options=True)
        st.text_input('메모',key='note_compact',max_chars=300,placeholder='짧은 손톱 / 반짝이 선호')
    with right:
        valid=False
        try:
            rgb=pick_color(st.session_state.color_compact)
            image=preview(rgb,st.session_state.pattern_compact,st.session_state.shape_compact)
            st.image(image,use_container_width=True)
            valid=True
        except (ValueError,TypeError):st.warning('색 이름이나 #FF99CC 형식으로 입력해주세요.')
        if st.session_state.pattern_compact not in PATTERNS:st.caption('직접 입력한 그림은 기록만 해요. 미리보기는 색만 표시해요.')
        if st.button('💾 가족 기록 저장',type='primary',use_container_width=True,disabled=not valid):
            name=st.session_state.name.strip()
            if not name or name=='＋ 새 가족':st.warning('가족 이름을 입력해주세요.')
            elif len(st.session_state.family_records)>=100 and name not in [r['이름'] for r in st.session_state.family_records]:st.warning('최대 100명까지 저장할 수 있어요.')
            else:
                row={'이름':name,'손톱 형태':st.session_state.shape_compact,'색상':st.session_state.color_compact,'그림':st.session_state.pattern_compact,'메모':st.session_state.note_compact}
                st.session_state.family_records=[r for r in st.session_state.family_records if r['이름']!=name]+[row]
                st.rerun()
        if valid:st.download_button('🖼 디자인 저장',png_bytes(image),'nail.png','image/png',use_container_width=True)
        if st.session_state.family_records:
            st.download_button('📥 가족 기록 저장',json.dumps(st.session_state.family_records,ensure_ascii=False,indent=2).encode('utf-8'),'family_nails.json','application/json',use_container_width=True)
        st.caption('종료 전 기록 파일을 저장하세요. 자동 영구 저장은 되지 않아요.')
    if st.session_state.family_records:
        st.dataframe(st.session_state.family_records,hide_index=True,use_container_width=True,height=145)
    # 보조 기능은 같은 화면의 작은 팝오버로 제공합니다.
    a,b=st.columns(2)
    with a.popover('📂 기록 불러오기',use_container_width=True):
        uploaded=st.file_uploader('기록 파일',type=['json'])
        if st.button('불러오기',disabled=uploaded is None):
            try:
                if uploaded.size>1_000_000:raise ValueError('1MB 이하 파일을 선택해주세요.')
                rows=validate_records(json.loads(uploaded.getvalue().decode('utf-8-sig')))
                merged={r['이름']:r for r in st.session_state.family_records}
                merged.update({r['이름']:r for r in rows})
                if len(merged)>100:raise ValueError('최대 100명까지 가능해요.')
                st.session_state.family_records=list(merged.values())
                st.rerun()
            except (ValueError,TypeError,UnicodeError) as exc:st.error(str(exc))
        st.caption('같은 이름은 파일의 기록으로 바뀝니다.')
    with b.popover('📱 QR 공유',use_container_width=True):
        url=st.text_input('앱 배포 주소',placeholder='https://your-app.streamlit.app').strip()
        if url:
            try:ok=len(url)<=1500 and valid_public_url(url)
            except ValueError:ok=False
            if ok:
                qr=qrcode.make(url).convert('RGB')
                st.image(qr,width=180)
                st.download_button('QR 저장',png_bytes(qr),'nail_qr.png','image/png')
                st.caption('앱 접속용이며 가족 기록은 포함되지 않아요.')
            else:st.warning('공개 HTTPS 주소를 넣어주세요.')


if __name__=='__main__':
    main()
