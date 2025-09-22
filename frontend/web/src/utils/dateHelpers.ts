// Firebase Timestamp를 Date 문자열로 변환하는 헬퍼 함수

export const formatDate = (date: any): string => {
  if (!date) return '날짜 없음';
  
  // Firebase Timestamp 객체인 경우
  if (date._seconds && date._nanoseconds) {
    const dateObject = new Date(date._seconds * 1000);
    return dateObject.toLocaleDateString('ko-KR');
  }
  
  // ISO 문자열인 경우
  if (typeof date === 'string') {
    const dateObject = new Date(date);
    if (!isNaN(dateObject.getTime())) {
      return dateObject.toLocaleDateString('ko-KR');
    }
  }
  
  // Date 객체인 경우
  if (date instanceof Date) {
    return date.toLocaleDateString('ko-KR');
  }
  
  // 기타
  return '날짜 형식 오류';
};

export const formatDateTime = (date: any): string => {
  if (!date) return '날짜 없음';
  
  // Firebase Timestamp 객체인 경우
  if (date._seconds && date._nanoseconds) {
    const dateObject = new Date(date._seconds * 1000);
    return dateObject.toLocaleString('ko-KR');
  }
  
  // ISO 문자열인 경우
  if (typeof date === 'string') {
    const dateObject = new Date(date);
    if (!isNaN(dateObject.getTime())) {
      return dateObject.toLocaleString('ko-KR');
    }
  }
  
  // Date 객체인 경우
  if (date instanceof Date) {
    return date.toLocaleString('ko-KR');
  }
  
  // 기타
  return '날짜 형식 오류';
};
