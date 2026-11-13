"""Pastel Nail Studio
실행: pip install -r requirements.txt && streamlit run app.py
배포: GitHub에 두 파일 업로드 → Streamlit Community Cloud에서 app.py 배포.
사진은 파일/DB에 저장하지 않으며 외부 AI 서비스로 전송하지 않습니다.
추천은 규칙 기반이며 사진 미리보기는 수동 합성(실제 시술 결과 아님)입니다.
"""
from io import BytesIO
import hashlib
import math
from urllib.parse import urlparse

import qrcode
import streamlit as st
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

PALETTE = {
    '밀키 핑크': '#F4B8CB', '라벤더': '#BFA8E5', '피치 코랄': '#F3AD99',
    '버터 옐로': '#F3DB8C', '민트': '#A5D8C3', '스카이 블루': '#9FC9E8',
    '로즈 베이지': '#C89698', '베리 핑크': '#CD527C', '밀크 화이트': '#F8F4EC',
}
PATTERNS = ['없음', '하트', '꽃', '도트', '프렌치', '고양이', '강아지', '토끼']
FINGERS = ['엄지', '검지', '중지', '약지', '소지']


def png_bytes(image):
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def recommend(tone, mood, favorite, animal='선택 안 함'):
    """취향을 우선하는 설명 가능한 규칙 기반 추천."""
    by_tone = {'따뜻한 톤': '피치 코랄', '차가운 톤': '라벤더',
               '중간 톤': '로즈 베이지', '잘 모르겠어요': '밀키 핑크'}
    by_mood = {'귀여운': ('밀키 핑크', '하트'), '청순한': ('밀크 화이트', '프렌치'),
               '산뜻한': ('민트', '꽃'), '화려한': ('베리 핑크', '도트')}
    accent, pattern = by_mood[mood]
    base = favorite if favorite != '추천받을래요' else by_tone[tone]
    if animal in ('고양이', '강아지', '토끼'):
        pattern = animal
    return base, accent, pattern


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
    st.set_page_config(page_title='말랑 네일 스튜디오', page_icon='💅', layout='centered')
    st.markdown('''<style>
    .stApp {background:linear-gradient(135deg,#fff5fa 0%,#f4efff 100%);color:#44314f;}
    h1,h2,h3 {color:#634375 !important;}
    .stButton > button,.stDownloadButton > button {border-radius:18px;border:1px solid #b77da3;background:#f5d6e8;color:#44314f;}
    div[data-testid="stExpander"] {border:1px solid #decde9;border-radius:18px;background:#ffffffaa;}
    .hero {padding:24px 20px;background:#ffffffb8;border:1px solid #ead8ee;border-radius:24px;margin-bottom:20px;}
    </style>''', unsafe_allow_html=True)
    st.markdown('''<div class="hero"><h1>💅 말랑 네일 스튜디오</h1>
    <p>내 취향에 맞는 색, 손끝에 피어나는 작은 그림.</p>
    <p>취향 추천 · 손 사진 미리보기 · QR로 공유하기</p></div>''', unsafe_allow_html=True)
    st.caption('피부 톤과 상관없이 좋아하는 색을 선택하세요. 모든 톤에 모든 색이 어울릴 수 있어요.')
    tab1, tab2, tab3 = st.tabs(['🎨 디자인 추천', '🖐️ 내 손에 미리보기', '📱 QR 접속'])
    with tab1:
        st.subheader('오늘은 어떤 네일이 끌리나요?')
        tone = st.selectbox('피부 톤 (사진 자동 분석 아님)', ['잘 모르겠어요', '따뜻한 톤', '차가운 톤', '중간 톤'])
        mood = st.selectbox('원하는 분위기', ['귀여운', '청순한', '산뜻한', '화려한'])
        favorite = st.selectbox('좋아하는 색', ['추천받을래요']+list(PALETTE))
        animal = st.selectbox('동물을 좋아하나요? 좋아하는 동물을 골라주세요', ['선택 안 함', '고양이', '강아지', '토끼'])
        base, accent, pattern = recommend(tone, mood, favorite, animal)
        st.caption('동물을 고르면 분위기 추천 그림 대신 선택한 동물 그림을 사용해요.')
        st.info(f'추천 조합: {base} + 포인트 {accent} / {pattern}')
        st.caption('좋아하는 색을 우선하고, 피부 톤과 분위기에 정해 둔 조합을 연결하는 규칙 기반 추천입니다. 생성형 AI는 사용하지 않습니다.')
        card = design_card(base, accent, pattern)
        st.image(card, caption='엄지 → 소지 순서의 디자인 보드 (약지 포인트)', use_container_width=True)
        st.download_button('디자인 보드 저장', png_bytes(card), 'nail_design.png', 'image/png')
        if st.button('이 조합을 사진에 적용', type='primary'):
            st.session_state['paint_color'] = base
            st.session_state['paint_pattern'] = pattern
            st.success('적용했어요! ‘내 손에 미리보기’ 탭을 열어주세요. 사진에는 선택한 기본 색상을 사용합니다.')
    with tab2:
        st.subheader('내 사진에 색과 그림 입히기')
        st.write('손등이 위로 오고 손가락이 펼쳐진 밝은 사진을 올려주세요. 손톱 위치는 직접 조절합니다.')
        st.caption('프렌치의 흰 끝은 스티커 상단입니다. 손톱 끝 방향에 맞춰 회전하세요.')
        source = st.radio('사진 가져오기', ['파일 업로드', '카메라 촬영'], horizontal=True)
        uploaded = (st.file_uploader('손 사진 (JPG·PNG·WEBP, 최대 10MB)', type=['jpg','jpeg','png','webp'])
                    if source == '파일 업로드' else st.camera_input('손 사진 촬영'))
        c1, c2 = st.columns(2)
        color_name = c1.selectbox('네일 색', list(PALETTE), key='paint_color')
        pattern_name = c2.selectbox('그림', PATTERNS, key='paint_pattern')
        custom = st.color_picker('직접 색을 고를 수도 있어요', PALETTE[color_name], key='custom_' + color_name)
        opacity = st.slider('색상 불투명도', 10, 100, 75)
        if uploaded is None:
            st.info('사진을 올리면 위치 조절과 미리보기가 나타나요.')
        else:
            raw = uploaded.getvalue()
            if len(raw) > 10*1024*1024:
                st.error('사진 크기가 10MB를 넘어요. 줄여서 다시 올려주세요.')
            else:
                try:
                    image = Image.open(BytesIO(raw))
                    if image.width*image.height > 25_000_000:
                        raise ValueError('사진이 너무 커요. 2,500만 화소 이하로 줄여주세요.')
                    image = ImageOps.exif_transpose(image).convert('RGBA')
                    image.thumbnail((1200, 1200))
                    w, h = image.size
                    photo_key = hashlib.sha256(raw).hexdigest()[:12]
                    st.caption('좌우·위아래는 사진 전체의 백분율입니다. 왼쪽 위는 (0, 0), 오른쪽 아래는 (100, 100).')
                    st.image(image, caption='원본: 손톱 위치를 확인하세요', use_container_width=True)
                    overlay = Image.new('RGBA', image.size, (0,0,0,0))
                    for i, finger in enumerate(FINGERS):
                        with st.expander(f'{finger} 위치·크기·각도', expanded=(i == 0)):
                            prefix = f'{photo_key}_{i}'
                            enabled = st.checkbox('이 손톱 표시', value=True, key=prefix+'on')
                            x = st.slider('좌우 위치 (%)', 0.0, 100.0, float(15+i*17), .5, key=prefix+'x')
                            y = st.slider('위아래 위치 (%)', 0.0, 100.0, 30.0, .5, key=prefix+'y')
                            width = st.slider('폭 (사진 너비 %)', 1.0, 20.0, 5.0, .5, key=prefix+'w')
                            height = st.slider('길이 (사진 높이 %)', 1.0, 25.0, 9.0, .5, key=prefix+'h')
                            angle = st.slider('회전 (도)', -180, 180, 0, key=prefix+'a')
                        if enabled:
                            patch = nail_patch(custom, pattern_name, w*width/100, h*height/100)
                            alpha = patch.getchannel('A').point(lambda p: round(p*opacity/100))
                            patch.putalpha(alpha)
                            patch = patch.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
                            overlay.alpha_composite(patch, (int(w*x/100-patch.width/2), int(h*y/100-patch.height/2)))
                    result = Image.alpha_composite(image, overlay).convert('RGB')
                    st.image(result, caption='수동 합성 미리보기 · 실제 발색과 다를 수 있어요', use_container_width=True)
                    st.download_button('내 네일 사진 저장', png_bytes(result), 'my_nail_preview.png', 'image/png')
                except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
                    st.error(f'사진을 열 수 없어요: {exc}')
        st.caption('사진을 파일이나 데이터베이스에 저장하지 않습니다. 업로드 사진은 앱 서버 메모리에서 처리되므로 민감한 사진은 피해주세요.')
    with tab3:
        st.subheader('QR을 찍으면 이 앱으로!')
        st.write('먼저 앱을 배포한 다음, 실제 공개 HTTPS 주소를 입력해주세요.')
        url = st.text_input('배포된 앱 주소', placeholder='https://your-app.streamlit.app')
        if url.strip():
            clean = url.strip()
            if len(clean) > 1500:
                st.warning('주소가 너무 길어요. 앱의 기본 배포 주소를 입력해주세요.')
            elif not valid_public_url(clean):
                st.warning('공개 HTTPS 주소를 입력해주세요. localhost 주소는 다른 휴대폰에서 접속할 수 없어요.')
            else:
                qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=9, border=4)
                qr.add_data(clean)
                qr.make(fit=True)
                qr_image = qr.make_image(fill_color='#44314F', back_color='white').convert('RGB')
                st.image(qr_image, width=280, caption='휴대폰 카메라로 스캔하세요')
                st.download_button('QR 이미지 저장', png_bytes(qr_image), 'nail_app_qr.png', 'image/png')
                st.link_button('입력한 주소 열기', clean)
                st.caption('QR에는 입력한 주소만 들어갑니다. 주소의 정확성과 공개 접속 가능 여부는 직접 확인해주세요. 사진이나 디자인 설정은 QR에 포함되지 않습니다.')
        with st.expander('GitHub + Streamlit 배포 방법', expanded=True):
            st.markdown('''1. GitHub 저장소에 **app.py**, **requirements.txt** 두 파일을 업로드합니다.
2. Streamlit Community Cloud에 GitHub 계정으로 로그인합니다.
3. **Create app**에서 저장소와 브랜치를 선택하고, Main file path를 `app.py`로 지정해 배포합니다.
4. 배포가 끝나면 공개 접속 가능한 앱 주소를 위에 붙여 넣습니다.
5. QR을 저장하고 휴대폰에서 접속을 확인합니다.

로컬 실행: `pip install -r requirements.txt` → `streamlit run app.py`

**주의:** GitHub에 파일을 올리는 것만으로 앱이 실행되지는 않습니다. GitHub Pages는 Python 서버 앱을 실행하지 않으므로 Streamlit 배포가 필요합니다. 비공개 앱은 QR로 접속해도 로그인이나 접근 권한이 필요합니다.''')
    st.divider()
    st.caption('💜 말랑 네일 스튜디오 · 파스텔로 채우는 나만의 손끝')


if __name__ == '__main__':
    main()
