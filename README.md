# Youtube Live Chat Overlay

Ung dung hien thi khung chat livestream Youtube len man hinh voi nen trong suot, ho tro doc tin nhan (TTS) va dich thuat.

## Tinh nang

- Hien thi chat Youtube tren man hinh (Overlay) voi nen trong suot.
- Doc tin nhan tu dong bang giong chi Google (TTS).
- Dich tin nhan tu dong (Anh sang Viet hoac Viet sang Anh).
- Tu dong chuyen doi tu long (slang) thanh cau hoan chinh truoc khi dich.
- Noi bat tin nhan cua Hoi vien (Member) va Super Chat.
- Bo loc tu cam (Blacklist).
- Tudong tim link livestream tu link kenh.
- Tuy chinh giao dien: co chu, do mo, mau sac, toc do hien thi.

## Cach cai dat

1. Cai dat Python 3.x tren may tinh cua ban.
2. Tai thu muc nay ve may.
3. Mo Terminal (Cmd/PowerShell) tai thu muc vua tai.
4. Cai dat cac thu vien can thiet bang lenh:
   pip install -r requirements.txt

## Cach su dung

1. Cach don gian nhat: Chay file `YouTubeChatOverlay.exe`.
   
2. Hoac chay bang Python (neu muon chinh sua code):
   python youtube_chat_overlay.py

2. Mot cua so se hien ra yeu cau nhap Link.
   - Ban co the nhap Link Video Livestream truc tiep.
   - Hoac nhap Link Kenh (Channel) Youtube, ung dung se tu tim livestream dang phat.

3. Sau khi ket noi thanh cong, khung chat se hien ra.
   - Keo tha o nut "::" de di chuyen khung chat.
   - Nhan nut banh rang de mo Cai dat (Settings).
   - Nhan nut "-" de an xuong khay he thong.

## Cau hinh nang cao

- File slang.json: Chua danh sach cac tu long (slang) can thay the. Ban co the mo bang Notepad de them/sua.
- File blacklist.txt: Chua danh sach cac tu cam. Tin nhan chua tu nay se bi an.
