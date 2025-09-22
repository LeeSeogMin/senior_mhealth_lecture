"""
Firestore 연동 모듈
GCP 운영 환경에서 과거 분석 결과 조회 및 저장
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from google.cloud import firestore
from google.oauth2 import service_account
import asyncio

logger = logging.getLogger(__name__)

# NotificationService import (필요시 활성화)
try:
    from .notification_service import notification_service
    # notification_service가 None일 수 있음 (Firebase 초기화 실패 시)
    NOTIFICATION_ENABLED = notification_service is not None
    if not NOTIFICATION_ENABLED:
        logger.warning("NotificationService가 비활성화되었습니다 (Firebase 초기화 실패)")
except ImportError as e:
    notification_service = None
    NOTIFICATION_ENABLED = False
    logger.warning(f"NotificationService를 가져올 수 없습니다: {e}")

class FirestoreConnector:
    """Firestore 데이터베이스 연동 클래스"""
    
    def __init__(self, credentials_path: Optional[str] = None, project_id: Optional[str] = None):
        """
        초기화
        
        Args:
            credentials_path: 서비스 계정 키 파일 경로
            project_id: GCP 프로젝트 ID
        """
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
        
        # 에뮬레이터 모드 감지
        emulator_host = os.getenv('FIRESTORE_EMULATOR_HOST')
        self.is_emulator = bool(emulator_host)
        
        if self.is_emulator:
            # 에뮬레이터 모드: 인증 없이 연결
            logger.info(f"🧪 Firestore 에뮬레이터 모드: {emulator_host}")
            os.environ['FIRESTORE_EMULATOR_HOST'] = emulator_host
            self.db = firestore.Client(project=self.project_id or 'demo-project')
            
        else:
            # 운영 모드: 인증 설정
            logger.info("🏢 Firestore 운영 모드")
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                self.db = firestore.Client(credentials=credentials, project=self.project_id)
            else:
                # 환경 변수에서 인증 정보 로드
                self.db = firestore.Client(project=self.project_id)
        
        # 컬렉션 이름
        self.analysis_collection = 'mental_health_analyses'
        self.users_collection = 'users'
        
        mode = "에뮬레이터" if self.is_emulator else "운영"
        logger.info(f"✅ Firestore 커넥터 초기화 완료 ({mode} 모드)")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        현재 연결 정보 반환
        
        Returns:
            연결 모드 및 상태 정보
        """
        return {
            'mode': 'emulator' if self.is_emulator else 'production',
            'project_id': self.project_id,
            'emulator_host': os.getenv('FIRESTORE_EMULATOR_HOST'),
            'is_emulator': self.is_emulator
        }
    
    def get_user_analysis_history(
        self,
        user_id: str,
        days_back: int = 30,
        limit: Optional[int] = None,
        use_new_schema: bool = True
    ) -> List[Dict[str, Any]]:
        """
        사용자의 과거 분석 기록 조회 (개선된 스키마 지원)
        
        Args:
            user_id: 사용자 ID
            days_back: 조회할 과거 일수
            limit: 최대 조회 개수
            use_new_schema: 새로운 스키마 사용 여부
            
        Returns:
            분석 기록 리스트 (시간순 정렬)
        """
        try:
            # 날짜 범위 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            if use_new_schema:
                # analyses 서브컬렉션에서 조회 (Backend에서 저장한 최종 분석 결과)
                query = (self.db.collection('users').document(user_id).collection('analyses')
                        .where(filter=('timestamp', '>=', start_date))
                        .where(filter=('timestamp', '<=', end_date))
                        .order_by('timestamp', direction=firestore.Query.DESCENDING))
            else:
                # 기존 mental_health_analyses 컬렉션에서 조회
                query = (self.db.collection(self.analysis_collection)
                        .where(filter=('user_id', '==', user_id))
                        .where(filter=('analysis_timestamp', '>=', start_date))
                        .where(filter=('analysis_timestamp', '<=', end_date))
                        .order_by('analysis_timestamp'))
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            
            # 결과 변환
            history = []
            for doc in docs:
                data = doc.to_dict()
                data['doc_id'] = doc.id
                
                if use_new_schema:
                    # analyses 컬렉션 스키마
                    transformed = data.get('transformedResult', {})
                    history_item = {
                        'analysisId': data.get('callId', doc.id),
                        'callId': data.get('callId'),
                        'timestamp': data.get('timestamp', datetime.now()).isoformat() if hasattr(data.get('timestamp'), 'isoformat') else str(data.get('timestamp')),
                        'coreIndicators': transformed.get('result', {}).get('coreIndicators', {}),
                        'integratedResults': transformed.get('result', {}),
                        'interpretation': data.get('interpretation', ''),
                        'metadata': transformed.get('metadata', {}),
                        'status': transformed.get('status', 'completed'),
                        'analysisType': data.get('analysisType', 'unknown')
                    }
                else:
                    # 기존 스키마 형식
                    history_item = {
                        'analysis_timestamp': data['analysis_timestamp'].isoformat() if hasattr(data.get('analysis_timestamp'), 'isoformat') else str(data.get('analysis_timestamp')),
                        'indicators': data.get('indicators', {}),
                        'risk_assessment': data.get('risk_assessment', {}),
                        'audio_duration': data.get('audio_duration', 0),
                        'processing_time': data.get('processing_time', 0)
                    }
                history.append(history_item)
            
            logger.info(f"사용자 {user_id}의 분석 기록 {len(history)}개 조회 완료 (스키마: {'새로운' if use_new_schema else '기존'})")
            return history
            
        except Exception as e:
            logger.error(f"분석 기록 조회 실패: {e}")
            return []
    
    def get_latest_analysis_with_indicators(
        self,
        user_id: str,
        senior_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        사용자의 최신 분석 결과 조회 (5대 지표 포함)
        
        Args:
            user_id: 사용자 ID
            senior_id: 시니어 ID (선택적)
            
        Returns:
            최신 분석 결과 또는 None
        """
        try:
            # 새로운 analyses 서브컬렉션에서 최신 결과 조회
            query = self.db.collection('users').document(user_id).collection('analyses')
            
            if senior_id:
                query = query.where(filter=('seniorId', '==', senior_id))
            
            query = query.order_by('createdAt', direction=firestore.Query.DESCENDING).limit(1)
            
            docs = list(query.stream())
            
            if docs:
                data = docs[0].to_dict()
                data['doc_id'] = docs[0].id
                
                # 5대 지표 정보 로깅
                if 'coreIndicators' in data:
                    indicators = data['coreIndicators']
                    logger.info(f"최신 분석 결과 조회 완료 - 5대 지표:")
                    for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
                        if key in indicators:
                            value = indicators[key].get('value', 'N/A')
                            level = indicators[key].get('level', 'N/A')
                            logger.info(f"  {key}: {value} ({level})")
                
                return data
            else:
                logger.info(f"사용자 {user_id}의 분석 결과가 없습니다")
                return None
                
        except Exception as e:
            logger.error(f"최신 분석 결과 조회 실패: {e}")
            return None
    
    def save_analysis_result(
        self,
        user_id: str,
        analysis_result: Dict[str, Any],
        audio_path: Optional[str] = None,
        call_id: Optional[str] = None,
        senior_id: Optional[str] = None
    ) -> bool:
        """
        분석 결과를 Firestore에 저장 (개선된 스키마 지원)
        
        Args:
            user_id: 사용자 ID
            analysis_result: 분석 결과
            audio_path: 오디오 파일 경로
            call_id: 통화 ID
            senior_id: 시니어 ID
            
        Returns:
            저장 성공 여부
        """
        try:
            # 새로운 스키마 형식 확인
            if 'coreIndicators' in analysis_result:
                # 개선된 스키마 형식으로 저장
                doc_data = {
                    'analysisId': call_id or analysis_result.get('analysisId'),
                    'callId': call_id or analysis_result.get('callId'),
                    'userId': user_id,
                    'seniorId': senior_id or analysis_result.get('seniorId', user_id),
                    
                    # 5대 핵심 지표
                    'coreIndicators': analysis_result.get('coreIndicators', {}),
                    
                    # 분석 방법론별 결과
                    'analysisMethodologies': analysis_result.get('analysisMethodologies', {}),
                    
                    # 통합 결과
                    'integratedResults': analysis_result.get('integratedResults', {}),
                    
                    # 해석 및 권장사항
                    'interpretation': analysis_result.get('interpretation', {}),
                    
                    # 메타데이터
                    'metadata': analysis_result.get('metadata', {}),
                    
                    # 타임스탬프
                    'createdAt': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP,
                    'analysisTimestamp': datetime.now(),
                    
                    # 상태
                    'status': analysis_result.get('status', 'completed'),
                    'hasAnalysis': True,
                    
                    # 오디오 정보
                    'audioPath': audio_path,
                    
                    # 레거시 호환성 (선택적)
                    'legacy': analysis_result.get('legacy', {})
                }
                
                # analyses 서브컬렉션에 저장
                if call_id:
                    # call_id가 있으면 해당 ID로 문서 생성
                    doc_ref = self.db.collection('users').document(user_id).collection('analyses').document(call_id)
                    doc_ref.set(doc_data)
                    doc_id = call_id
                else:
                    # call_id가 없으면 자동 ID 생성
                    doc_ref = self.db.collection('users').document(user_id).collection('analyses').add(doc_data)
                    doc_id = doc_ref[1].id
                
                # calls 서브컬렉션 업데이트 (연결된 통화가 있는 경우)
                if call_id and senior_id:
                    call_ref = self.db.collection('users').document(user_id).collection('calls').document(call_id)
                    call_ref.update({
                        'hasAnalysis': True,
                        'analysisCompletedAt': firestore.SERVER_TIMESTAMP,
                        'analysisStatus': 'completed',
                        'updatedAt': firestore.SERVER_TIMESTAMP
                    })
                
                logger.info(f"✅ 개선된 스키마로 분석 결과 저장 완료: {user_id} -> {doc_id}")
                logger.info(f"   5대 지표: DRI={doc_data['coreIndicators'].get('DRI', {}).get('value', 'N/A')}, "
                          f"SDI={doc_data['coreIndicators'].get('SDI', {}).get('value', 'N/A')}, "
                          f"CFL={doc_data['coreIndicators'].get('CFL', {}).get('value', 'N/A')}, "
                          f"ES={doc_data['coreIndicators'].get('ES', {}).get('value', 'N/A')}, "
                          f"OV={doc_data['coreIndicators'].get('OV', {}).get('value', 'N/A')}")

                # FCM 알림 전송 (비동기)
                if NOTIFICATION_ENABLED and notification_service:
                    try:
                        # 시니어 이름 가져오기
                        senior_name = "시니어"  # 기본값
                        if senior_id:
                            senior_doc = self.db.collection('users').document(user_id).collection('seniors').document(senior_id).get()
                            if senior_doc.exists:
                                senior_name = senior_doc.to_dict().get('name', '시니어')

                        # 비동기 알림 전송
                        asyncio.create_task(
                            notification_service.send_analysis_complete_notification(
                                user_id=user_id,
                                analysis_id=doc_id,
                                senior_name=senior_name,
                                analysis_type='comprehensive'
                            )
                        )
                        logger.info(f"📱 FCM 알림 전송 요청: {user_id} -> {doc_id}")
                    except Exception as e:
                        logger.error(f"FCM 알림 전송 실패: {e}")
                        # 알림 실패해도 분석 결과 저장은 성공으로 처리

            else:
                # 기존 스키마 형식으로 저장 (하위 호환성)
                doc_data = {
                    'user_id': user_id,
                    'analysis_timestamp': datetime.now(),
                    'audio_path': audio_path,
                    'indicators': analysis_result.get('indicators', {}),
                    'risk_assessment': analysis_result.get('risk_assessment', {}),
                    'trend_analysis': analysis_result.get('trend_analysis'),
                    'comprehensive_interpretation': analysis_result.get('comprehensive_interpretation'),
                    'audio_duration': analysis_result.get('voice_analysis', {}).get('duration', 0),
                    'processing_time': analysis_result.get('processing_time', 0),
                    'status': analysis_result.get('status', 'success'),
                    'created_at': firestore.SERVER_TIMESTAMP
                }
                
                # Firestore에 저장
                doc_ref = self.db.collection(self.analysis_collection).add(doc_data)
                doc_id = doc_ref[1].id
                
                logger.info(f"기존 스키마로 분석 결과 저장 완료: {user_id} -> {doc_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"분석 결과 저장 실패: {e}")
            return False
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 프로필 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            사용자 프로필 정보
        """
        try:
            doc_ref = self.db.collection(self.users_collection).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                profile = doc.to_dict()
                logger.info(f"사용자 프로필 조회 완료: {user_id}")
                return profile
            else:
                logger.warning(f"사용자 프로필 없음: {user_id}")
                return self._create_default_profile(user_id)
                
        except Exception as e:
            logger.error(f"사용자 프로필 조회 실패: {e}")
            return self._create_default_profile(user_id)
    
    def _create_default_profile(self, user_id: str) -> Dict[str, Any]:
        """기본 사용자 프로필 생성"""
        return {
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'age': None,
            'gender': None,
            'medical_history': [],
            'preferences': {}
        }
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        사용자 프로필 업데이트
        
        Args:
            user_id: 사용자 ID
            profile_data: 업데이트할 프로필 데이터
            
        Returns:
            업데이트 성공 여부
        """
        try:
            doc_ref = self.db.collection(self.users_collection).document(user_id)
            
            # 업데이트 데이터 준비
            update_data = profile_data.copy()
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            # Firestore 업데이트
            doc_ref.set(update_data, merge=True)
            
            logger.info(f"사용자 프로필 업데이트 완료: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"사용자 프로필 업데이트 실패: {e}")
            return False
    
    def get_analysis_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        분석 통계 조회
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            분석 통계 정보
        """
        try:
            # 기본 날짜 범위 설정
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # 기간 내 분석 수 조회
            query = (self.db.collection(self.analysis_collection)
                    .where('analysis_timestamp', '>=', start_date)
                    .where('analysis_timestamp', '<=', end_date))
            
            docs = list(query.stream())
            
            # 통계 계산
            total_analyses = len(docs)
            unique_users = len(set(doc.to_dict().get('user_id') for doc in docs))
            
            # 위험 수준별 분포
            risk_distribution = {'low': 0, 'moderate': 0, 'high': 0}
            for doc in docs:
                data = doc.to_dict()
                risk_level = data.get('risk_assessment', {}).get('overall_risk', 'unknown')
                if risk_level in risk_distribution:
                    risk_distribution[risk_level] += 1
            
            statistics = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_analyses': total_analyses,
                'unique_users': unique_users,
                'risk_distribution': risk_distribution,
                'average_analyses_per_user': total_analyses / unique_users if unique_users > 0 else 0
            }
            
            logger.info(f"분석 통계 조회 완료: {total_analyses}건")
            return statistics
            
        except Exception as e:
            logger.error(f"분석 통계 조회 실패: {e}")
            return {}
    
    def delete_user_data(self, user_id: str, confirm: bool = False) -> bool:
        """
        사용자 데이터 완전 삭제 (GDPR 준수)
        
        Args:
            user_id: 사용자 ID
            confirm: 삭제 확인
            
        Returns:
            삭제 성공 여부
        """
        if not confirm:
            logger.warning("사용자 데이터 삭제는 confirm=True로 호출해야 합니다")
            return False
        
        try:
            # 분석 기록 삭제
            analyses_query = self.db.collection(self.analysis_collection).where('user_id', '==', user_id)
            analyses_docs = analyses_query.stream()
            
            deleted_count = 0
            for doc in analyses_docs:
                doc.reference.delete()
                deleted_count += 1
            
            # 사용자 프로필 삭제
            user_doc_ref = self.db.collection(self.users_collection).document(user_id)
            user_doc_ref.delete()
            
            logger.info(f"사용자 데이터 삭제 완료: {user_id} (분석기록 {deleted_count}건)")
            return True
            
        except Exception as e:
            logger.error(f"사용자 데이터 삭제 실패: {e}")
            return False
