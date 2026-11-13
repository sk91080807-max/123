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
from PIL import Image, ImageDraw

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

def main():
    st.set_page_config(page_title='말랑 네일', page_icon='💅', layout='centered')
    st.markdown('''<style>
    .stApp {background:linear-gradient(135deg,#fff5fa,#f1eaff);color:#493356;color-scheme:light;}
    .block-container {max-width:720px;padding-top:1.5rem;padding-bottom:1rem;}
    h1,h2,h3,p,label {color:#493356 !important;}
    h1 {font-size:2rem !important;text-align:center;}
    .stButton>button,.stDownloadButton>button,.stLinkButton>a {
      background:#fff9fd !important;color:#493356 !important;
      border:1px solid #b98ec9 !important;border-radius:16px;min-height:46px;}
    .stButton>button[kind="primary"] {background:#e7c8ee !important;border:2px solid #80538f !important;}
    .stButton>button p,.stDownloadButton>button p {color:#493356 !important;}
    [data-testid="stExpander"] {background:#ffffffb0;border:1px solid #d7b8e2;border-radius:16px;}
    [data-testid="stTextInput"] input {background:#ffffff !important;color:#493356 !important;-webkit-text-fill-color:#493356 !important;}
    [data-testid="stCaptionContainer"] p {color:#705d7c !important;}
    </style>''', unsafe_allow_html=True)
    if 'color' not in st.session_state:
        st.session_state.color = '밀키 핑크'
    if 'pattern' not in st.session_state:
        st.session_state.pattern = '하트'
    st.title('💅 말랑 네일')
    st.markdown('**① 색 고르기**')
    colors = [('🩷 핑크','밀키 핑크'),('💜 보라','라벤더'),('🧡 피치','피치 코랄'),
              ('💛 노랑','버터 옐로'),('💚 민트','민트'),('🩵 하늘','스카이 블루')]
    for start in (0,3):
        cols = st.columns(3)
        for col, (label, name) in zip(cols, colors[start:start+3]):
            if col.button(label, key='color_'+name, use_container_width=True,
                          type='primary' if st.session_state.color == name else 'secondary'):
                st.session_state.color = name
                st.rerun()
    st.markdown('**② 그림 고르기**')
    patterns = [('🤍 없음','없음'),('💕 하트','하트'),('🌼 꽃','꽃'),('🔵 도트','도트'),
                ('✨ 프렌치','프렌치'),('🐱 고양이','고양이'),('🐶 강아지','강아지'),('🐰 토끼','토끼')]
    for start in (0,4):
        cols = st.columns(4)
        for col, (label, name) in zip(cols, patterns[start:start+4]):
            if col.button(label, key='pattern_'+name, use_container_width=True,
                          type='primary' if st.session_state.pattern == name else 'secondary'):
                st.session_state.pattern = name
                st.rerun()
    image = design_card(st.session_state.color, st.session_state.color, st.session_state.pattern)
    st.image(image, use_container_width=True)
    st.caption(f'{st.session_state.color} · {st.session_state.pattern}')
    st.download_button('📥 내 네일 저장', png_bytes(image), 'my_nail.png', 'image/png', use_container_width=True)
    with st.expander('📱 QR 공유'):
        url = st.text_input('배포된 앱 주소', placeholder='https://your-app.streamlit.app')
        clean = url.strip()
        if clean:
            try:
                valid = len(clean) <= 1500 and valid_public_url(clean)
            except ValueError:
                valid = False
            if not valid:
                st.warning('공개 HTTPS 앱 주소를 넣어주세요.')
            else:
                qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
                qr.add_data(clean)
                qr.make(fit=True)
                qr_image = qr.make_image(fill_color='#493356', back_color='white').convert('RGB')
                st.image(qr_image, width=220)
                st.download_button('📥 QR 저장', png_bytes(qr_image), 'nail_qr.png', 'image/png', use_container_width=True)
                st.caption('QR은 앱 접속용이에요. 선택한 디자인은 사진으로 저장하세요.')


if __name__ == '__main__':
    main()
