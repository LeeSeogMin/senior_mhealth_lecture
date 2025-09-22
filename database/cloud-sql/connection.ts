// Cloud SQL MySQL 연결 설정
// Phase 1: 기초 인프라 구축 - Cloud SQL 연결

import mysql from 'mysql2/promise';

// 환경변수에서 설정 가져오기
const {
  DB_HOST = 'localhost',
  DB_PORT = '3306',
  DB_NAME = 'senior_mhealth',
  DB_USER = 'root',
  DB_PASSWORD = '',
  DB_SSL = 'false'
} = process.env;

// 연결 설정
const config = {
  host: DB_HOST,
  port: parseInt(DB_PORT),
  database: DB_NAME,
  user: DB_USER,
  password: DB_PASSWORD,
  ssl: DB_SSL === 'true' ? { rejectUnauthorized: false } : false,
  connectionLimit: 20, // 최대 연결 수
  acquireTimeout: 30000,
  timeout: 2000,
  charset: 'utf8mb4',
  timezone: '+09:00', // 한국 시간대
};

// 연결 풀 생성
const pool = mysql.createPool(config);

// 연결 테스트
pool.on('connection', (connection) => {
  console.log('✅ Cloud SQL MySQL 연결 성공');
  
  // 연결 설정
  connection.query('SET time_zone = "+09:00"');
  connection.query('SET NAMES utf8mb4');
});

pool.on('error', (err) => {
  console.error('❌ Cloud SQL MySQL 연결 오류:', err);
});

// 연결 풀 종료
process.on('SIGINT', async () => {
  await pool.end();
  console.log('Cloud SQL MySQL 연결 풀 종료');
  process.exit(0);
});

export default pool;
