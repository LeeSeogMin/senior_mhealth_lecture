"""
Cloud Function for Audio Preprocessing
경량 작업만 처리하여 메인 서비스 부담 감소
"""
import functions_framework
import tempfile
import librosa
import numpy as np
from google.cloud import storage

@functions_framework.http
def preprocess_audio(request):
    """
    음성 파일 전처리 (Cloud Function)
    - 노이즈 제거
    - 샘플링 레이트 조정
    - 특징 추출
    """
    request_json = request.get_json(silent=True)

    if not request_json or 'audio_path' not in request_json:
        return {'error': 'audio_path required'}, 400

    audio_path = request_json['audio_path']

    try:
        # GCS에서 오디오 다운로드
        client = storage.Client()
        bucket_name, blob_path = audio_path.replace('gs://', '').split('/', 1)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        # 임시 파일로 다운로드
        with tempfile.NamedTemporaryFile(suffix='.wav') as tmp_file:
            blob.download_to_filename(tmp_file.name)

            # librosa로 처리
            y, sr = librosa.load(tmp_file.name, sr=16000)

            # 노이즈 제거
            y_denoised = librosa.effects.preemphasis(y)

            # MFCC 특징 추출
            mfcc = librosa.feature.mfcc(y=y_denoised, sr=sr, n_mfcc=13)

            # 결과 반환
            return {
                'status': 'success',
                'features': {
                    'mfcc': mfcc.tolist(),
                    'duration': len(y) / sr,
                    'sample_rate': sr
                }
            }

    except Exception as e:
        return {'error': str(e)}, 500