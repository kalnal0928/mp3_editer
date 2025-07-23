import sys
import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TRCK, APIC
from pydub import AudioSegment

# --- Helper Functions ---

def get_tag_frame(audio, tag_name):
    """Safely get a tag frame from the audio file."""
    return audio.get(tag_name, type('', (object,), {'text': ['']})())

def parse_time(time_str):
    """Parse time string (MM:SS or SSS) into milliseconds."""
    try:
        if ':' in time_str:
            mins, secs = map(int, time_str.split(':'))
            return (mins * 60 + secs) * 1000
        else:
            return int(time_str) * 1000
    except ValueError:
        return None

# --- Mode 1: Tag Editor ---

def tag_editor_mode():
    """Handles all logic for editing MP3 metadata tags."""
    file_path = input("편집할 MP3 파일의 경로를 입력하세요: ")
    if not os.path.exists(file_path):
        print(f"오류: 파일을 찾을 수 없습니다 - {file_path}")
        return

    try:
        audio = MP3(file_path, ID3=ID3)
    except Exception as e:
        print(f"오류: MP3 파일을 열 수 없습니다. ({e})")
        return

    if audio.tags is None:
        audio.add_tags()

    title = get_tag_frame(audio.tags, 'TIT2').text[0]
    artist = get_tag_frame(audio.tags, 'TPE1').text[0]
    album = get_tag_frame(audio.tags, 'TALB').text[0]
    genre = get_tag_frame(audio.tags, 'TCON').text[0]
    track = get_tag_frame(audio.tags, 'TRCK').text[0]
    has_album_art = bool(audio.tags.getall('APIC'))

    print("--- 기존 MP3 태그 정보 ---")
    print(f"제목: {title}")
    print(f"아티스트: {artist}")
    print(f"앨범: {album}")
    print(f"장르: {genre}")
    print(f"트랙 번호: {track}")
    print(f"앨범 아트: {'있음' if has_album_art else '없음'}")
    print("-" * 28)

    print("새로운 태그 정보를 입력하세요. (변경 없으면 Enter)")
    new_title = input(f"새 제목 ({title}): ") or title
    new_artist = input(f"새 아티스트 ({artist}): ") or artist
    new_album = input(f"새 앨범 ({album}): ") or album
    new_genre = input(f"새 장르 ({genre}): ") or genre
    new_track = input(f"새 트랙 ({track}): ") or track

    audio.tags['TIT2'] = TIT2(encoding=3, text=new_title)
    audio.tags['TPE1'] = TPE1(encoding=3, text=new_artist)
    audio.tags['TALB'] = TALB(encoding=3, text=new_album)
    audio.tags['TCON'] = TCON(encoding=3, text=new_genre)
    audio.tags['TRCK'] = TRCK(encoding=3, text=new_track)

    new_art_path = input("새 앨범 아트 이미지 경로 (없으면 Enter): ")
    if new_art_path and os.path.exists(new_art_path):
        try:
            with open(new_art_path, 'rb') as art_file:
                audio.tags.delall('APIC')
                audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=art_file.read()))
            print("앨범 아트가 성공적으로 변경되었습니다.")
        except Exception as e:
            print(f"오류: 앨범 아트 처리 중 문제 발생. ({e})")
    elif new_art_path:
        print("경고: 앨범 아트 파일을 찾을 수 없습니다.")

    try:
        audio.save()
        print("\n태그 저장이 완료되었습니다.")
    except Exception as e:
        print(f"오류: 파일 저장 중 문제 발생. ({e})")

# --- Mode 2: Audio Editor ---

def audio_editor_mode():
    """Handles all logic for cutting and merging MP3 files."""
    print("--- 오디오 편집 모드 ---")
    print("1: MP3 파일 자르기")
    print("2: MP3 파일 붙이기")
    choice = input("원하는 작업을 선택하세요 (1 또는 2): ")

    if choice == '1':
        cut_mp3()
    elif choice == '2':
        merge_mp3()
    else:
        print("잘못된 선택입니다.")

def cut_mp3():
    """Cuts a section of an MP3 file and saves it as a new file."""
    file_path = input("자를 MP3 파일 경로: ")
    start_time_str = input("시작 시간 (예: 1:25 또는 85): ")
    end_time_str = input("종료 시간 (예: 2:30 또는 150): ")
    output_path = input("저장할 파일 이름 (예: output.mp3): ")

    start_ms = parse_time(start_time_str)
    end_ms = parse_time(end_time_str)

    if not os.path.exists(file_path):
        print("오류: 원본 파일을 찾을 수 없습니다.")
        return
    if start_ms is None or end_ms is None or start_ms >= end_ms:
        print("오류: 시간 형식이 잘못되었거나, 시작 시간이 종료 시간보다 큽니다.")
        return

    try:
        print("파일을 로드하는 중...")
        audio = AudioSegment.from_mp3(file_path)
        print("오디오를 자르는 중...")
        cut_audio = audio[start_ms:end_ms]
        print(f"'{output_path}' 파일로 저장하는 중...")
        cut_audio.export(output_path, format="mp3")
        print("파일 자르기가 완료되었습니다!")
    except Exception as e:
        print(f"오류 발생: {e}")

def merge_mp3():
    """Merges two MP3 files into a new file."""
    file1_path = input("첫 번째 MP3 파일 경로: ")
    file2_path = input("두 번째 MP3 파일 경로 (첫 번째 파일에 이어 붙일 파일): ")
    output_path = input("저장할 파일 이름 (예: merged.mp3): ")

    if not os.path.exists(file1_path) or not os.path.exists(file2_path):
        print("오류: 하나 또는 두 개의 원본 파일을 찾을 수 없습니다.")
        return

    try:
        print("첫 번째 파일을 로드하는 중...")
        audio1 = AudioSegment.from_mp3(file1_path)
        print("두 번째 파일을 로드하는 중...")
        audio2 = AudioSegment.from_mp3(file2_path)
        print("파일을 합치는 중...")
        merged_audio = audio1 + audio2
        print(f"'{output_path}' 파일로 저장하는 중...")
        merged_audio.export(output_path, format="mp3")
        print("파일 붙이기가 완료되었습니다!")
    except Exception as e:
        print(f"오류 발생: {e}")

# --- Main Application Logic ---

def main():
    """Main function to run the application."""
    print("===== MP3 편집기 =====")
    print("1: 태그 편집 모드")
    print("2: 오디오 편집 모드")
    main_choice = input("원하는 작업 모드를 선택하세요 (1 또는 2): ")

    if main_choice == '1':
        tag_editor_mode()
    elif main_choice == '2':
        audio_editor_mode()
    else:
        print("잘못된 선택입니다. 프로그램을 종료합니다.")

if __name__ == "__main__":
    main()