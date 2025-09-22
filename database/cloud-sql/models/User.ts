// 사용자 모델 (MySQL)
// Phase 1: 기초 인프라 구축 - Cloud SQL 모델

import pool from '../connection';
import { RowDataPacket, ResultSetHeader } from 'mysql2';

export interface User extends RowDataPacket {
  id?: number;
  uid: string;
  email: string;
  display_name?: string;
  phone_number?: string;
  role: 'caregiver' | 'senior' | 'admin';
  created_at?: Date;
  updated_at?: Date;
  is_active?: boolean;
}

export class UserModel {
  // 사용자 생성
  static async create(user: User): Promise<User> {
    const query = `
      INSERT INTO users (uid, email, display_name, phone_number, role)
      VALUES (?, ?, ?, ?, ?)
    `;
    
    const values = [
      user.uid,
      user.email,
      user.display_name,
      user.phone_number,
      user.role
    ];

    const [result] = await pool.execute<ResultSetHeader>(query, values);
    
    // 생성된 사용자 조회
    const [rows] = await pool.execute<User[]>(
      'SELECT * FROM users WHERE id = ?',
      [result.insertId]
    );
    
    return rows[0];
  }

  // UID로 사용자 조회
  static async findByUid(uid: string): Promise<User | null> {
    const [rows] = await pool.execute<User[]>(
      'SELECT * FROM users WHERE uid = ?',
      [uid]
    );
    return rows[0] || null;
  }

  // 이메일로 사용자 조회
  static async findByEmail(email: string): Promise<User | null> {
    const [rows] = await pool.execute<User[]>(
      'SELECT * FROM users WHERE email = ?',
      [email]
    );
    return rows[0] || null;
  }

  // 사용자 정보 업데이트
  static async update(uid: string, updates: Partial<User>): Promise<User | null> {
    const fields = Object.keys(updates).map(key => `${key} = ?`);
    const query = `
      UPDATE users 
      SET ${fields.join(', ')}
      WHERE uid = ?
    `;
    
    const values = [...Object.values(updates), uid];
    await pool.execute(query, values);
    
    // 업데이트된 사용자 조회
    return this.findByUid(uid);
  }

  // 사용자 비활성화
  static async deactivate(uid: string): Promise<boolean> {
    const [result] = await pool.execute<ResultSetHeader>(
      'UPDATE users SET is_active = false WHERE uid = ?',
      [uid]
    );
    return result.affectedRows > 0;
  }

  // 보호자 목록 조회
  static async getCaregivers(): Promise<User[]> {
    const [rows] = await pool.execute<User[]>(`
      SELECT * FROM users 
      WHERE role = 'caregiver' AND is_active = true
      ORDER BY created_at DESC
    `);
    return rows;
  }

  // 시니어 목록 조회
  static async getSeniors(): Promise<User[]> {
    const [rows] = await pool.execute<User[]>(`
      SELECT * FROM users 
      WHERE role = 'senior' AND is_active = true
      ORDER BY created_at DESC
    `);
    return rows;
  }
}
