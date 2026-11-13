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
    st.set_page_config(page_title='우리 가족 네일', page_icon='💅', layout='centered')
    st.markdown('''<style>
    .stApp{background:linear-gradient(135deg,#fff5fa,#f1eaff);color:#493356;color-scheme:light;}
    .block-container{max-width:760px;padding-top:4.5rem;padding-bottom:3rem;}
    h1{font-size:clamp(1.45rem,5vw,2rem)!important;line-height:1.5!important;overflow:visible!important;white-space:normal!important;}
    h1,h2,h3,p,label{color:#493356!important;}
    .stButton button,.stDownloadButton button{min-height:48px;height:auto!important;padding:10px 8px!important;border-radius:15px;border:1px solid #b58ac8;}
    .stButton button p,.stDownloadButton button p{white-space:normal!important;overflow:visible!important;line-height:1.5!important;}
    button[kind="primary"]{background:#e9cced!important;border:2px solid #80538f!important;}
    input,textarea{background:#fff!important;color:#493356!important;-webkit-text-fill-color:#493356!important;}
    </style>''', unsafe_allow_html=True)
    defaults={'family_records':[], 'edit_name':'', 'shape':'둥근형','shape_note':'', 'color_text':'밀키 핑크','pattern_text':'하트','memo':''}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
    st.title('💅 우리 가족 네일')
    st.text_input('가족 이름', key='edit_name', placeholder='예: 엄마', max_chars=40)
    st.selectbox('손톱 형태', SHAPES, key='shape')
    if st.session_state.shape=='직접 입력':
        st.text_input('형태 직접 입력', key='shape_note', max_chars=80)
    st.markdown('**색 고르기**')
    colors=list(PALETTE)
    for start in range(0,len(colors),3):
        for col,name in zip(st.columns(3),colors[start:start+3]):
            col.button(name,key='color_'+name,on_click=set_choice,args=('color_text',name),use_container_width=True,
                       type='primary' if st.session_state.color_text==name else 'secondary')
    st.text_input('색 직접 입력',key='color_text',placeholder='예: 빨강 / red / #FF99CC',max_chars=60)
    chosen=st.color_picker('색상표에서 선택', key='picker', value='#F4B8CB')
    st.button('이 색 적용',on_click=set_choice,args=('color_text',chosen),use_container_width=True)
    st.markdown('**그림 고르기**')
    for start in range(0,len(PATTERNS),2):
        for col,name in zip(st.columns(2),PATTERNS[start:start+2]):
            col.button(name,key='pattern_'+name,on_click=set_choice,args=('pattern_text',name),use_container_width=True,
                       type='primary' if st.session_state.pattern_text==name else 'secondary')
    st.text_input('그림 직접 입력',key='pattern_text',placeholder='예: 별 / 나비 / 곰돌이',max_chars=80)
    pattern=st.session_state.pattern_text.strip()
    shape=st.session_state.shape_note.strip() if st.session_state.shape=='직접 입력' else st.session_state.shape
    try:
        rgb=pick_color(st.session_state.color_text)
        image=preview(rgb,pattern,shape)
        st.image(image,use_container_width=True)
        if pattern not in PATTERNS:
            st.caption('직접 입력한 그림은 취향으로 기록돼요. 미리보기에는 색만 표시해요.')
        if shape in ('타원형','아몬드형') or st.session_state.shape=='직접 입력':
            st.caption('손톱 형태는 참고용 그림이에요. 아몬드형은 타원으로 표시해요.')
        st.download_button('📥 디자인 저장',png_bytes(image),'nail.png','image/png',use_container_width=True)
        valid_color=True
    except (ValueError,TypeError):
        st.warning('색 이름 또는 #FF99CC 같은 색상 코드를 입력해주세요.')
        valid_color=False
    st.text_input('취향 메모',key='memo',placeholder='예: 짧은 손톱, 반짝이는 디자인 선호',max_chars=300)
    if st.button('💾 가족 기록 저장',type='primary',use_container_width=True,disabled=not valid_color):
        name=st.session_state.edit_name.strip()
        if not name or not shape or not pattern:
            st.warning('이름·손톱 형태·그림을 입력해주세요. 그림이 없으면 ‘없음’을 선택하세요.')
        else:
            row={'이름':name,'손톱 형태':shape,'색상':st.session_state.color_text.strip(),'그림':pattern,'메모':st.session_state.memo.strip()}
            records=st.session_state.family_records
            if len(records)>=100 and name not in [r['이름'] for r in records]:
                st.warning('최대 100명까지 기록할 수 있어요.')
            else:
                st.session_state.family_records=[r for r in records if r['이름']!=name]+[row]
                st.success('저장했어요. 같은 이름은 기존 기록을 수정해요.')
    st.markdown('**우리 가족 기록**')
    records=st.session_state.family_records
    if records:
        st.dataframe(records,hide_index=True,use_container_width=True)
        selected=st.selectbox('수정할 가족', [r['이름'] for r in records])
        def load_member():
            row=next(r for r in st.session_state.family_records if r['이름']==selected)
            for key,field in [('edit_name','이름'),('color_text','색상'),('pattern_text','그림'),('memo','메모')]:
                st.session_state[key]=row[field]
            st.session_state.shape=row['손톱 형태'] if row['손톱 형태'] in SHAPES[:-1] else '직접 입력'
            st.session_state.shape_note=row['손톱 형태']
        st.button('✏️ 기록 불러와 수정',on_click=load_member,use_container_width=True)
        payload=json.dumps(records,ensure_ascii=False,indent=2).encode('utf-8')
        st.download_button('📥 가족 기록 파일 저장',payload,'family_nails.json','application/json',use_container_width=True)
    else:
        st.caption('아직 기록이 없어요.')
    st.caption('기록은 현재 접속 중에만 유지돼요. 종료 전 파일로 저장해주세요. 다른 휴대폰과 자동 공유되지 않아요.')
    with st.expander('📂 저장한 기록 불러오기'):
        uploaded=st.file_uploader('가족 기록 JSON',type=['json'])
        if st.button('기록 합치기',disabled=uploaded is None,use_container_width=True):
            try:
                if uploaded.size>1_000_000: raise ValueError('1MB 이하 파일만 가능해요.')
                rows=validate_records(json.loads(uploaded.getvalue().decode('utf-8-sig')))
                combined={r['이름']:r for r in st.session_state.family_records}
                combined.update({r['이름']:r for r in rows})
                if len(combined)>100: raise ValueError('최대 100명까지 가능해요.')
                st.session_state.family_records=list(combined.values())
                st.rerun()
            except (ValueError,TypeError,UnicodeError,KeyError) as exc:
                st.error(str(exc))
        st.caption('같은 이름은 파일 속 기록으로 바뀌어요.')
    with st.expander('📱 앱 QR 만들기'):
        url=st.text_input('배포 주소',placeholder='https://your-app.streamlit.app').strip()
        if url:
            try: valid=len(url)<=1500 and valid_public_url(url)
            except ValueError: valid=False
            if valid:
                qr=qrcode.make(url).convert('RGB')
                st.image(qr,width=220)
                st.download_button('QR 저장',png_bytes(qr),'nail_qr.png','image/png')
                st.caption('앱 접속용 QR이에요. 가족 기록은 포함되지 않아요.')
            else: st.warning('공개 HTTPS 주소를 입력해주세요.')


if __name__=='__main__':
    main()
