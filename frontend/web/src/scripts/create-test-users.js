// 테스트 사용자 생성 스크립트
const admin = require('firebase-admin');
const serviceAccount = require('../../../../firebase-service-account.json');

// Firebase Admin SDK 초기화
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
  projectId: 'thematic-center-463215-m2'
});

const auth = admin.auth();

async function createTestUsers() {
  const testUsers = [
    {
      email: 'caregiver1@example.com',
      password: 'password123',
      displayName: '보호자 1'
    },
    {
      email: 'caregiver2@example.com', 
      password: 'password123',
      displayName: '보호자 2'
    },
    {
      email: 'test@example.com',
      password: 'test123',
      displayName: '테스트 사용자'
    }
  ];

  for (const user of testUsers) {
    try {
      // 기존 사용자 확인
      try {
        const existingUser = await auth.getUserByEmail(user.email);
        console.log(`사용자 이미 존재: ${user.email} (UID: ${existingUser.uid})`);
        continue;
      } catch (error) {
        // 사용자가 없으면 생성
      }

      // 새 사용자 생성
      const newUser = await auth.createUser({
        email: user.email,
        password: user.password,
        displayName: user.displayName,
        emailVerified: true
      });

      console.log(`사용자 생성 완료: ${user.email} (UID: ${newUser.uid})`);
    } catch (error) {
      console.error(`사용자 생성 실패 (${user.email}):`, error.message);
    }
  }
}

// 스크립트 실행
createTestUsers()
  .then(() => {
    console.log('\n테스트 사용자 생성 완료!');
    console.log('\n로그인 정보:');
    console.log('- caregiver1@example.com / password123');
    console.log('- caregiver2@example.com / password123');
    console.log('- test@example.com / test123');
    process.exit(0);
  })
  .catch((error) => {
    console.error('스크립트 실행 오류:', error);
    process.exit(1);
  });