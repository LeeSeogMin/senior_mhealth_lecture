// 시니어 모델 (MySQL)
// Phase 1: 기초 인프라 구축 - Cloud SQL 모델

import pool from '../connection';
import { RowDataPacket, ResultSetHeader } from 'mysql2';

export interface Senior extends RowDataPacket {
  id?: number;
  user_id: number;
  name: string;
  birth_date?: Date;
  gender?: string;
  address?: string;
  emergency_contact?: string;
  medical_history?: string;
  created_at?: Date;
  updated_at?: Date;
}

export interface SeniorWithCaregiver extends Senior {
  caregiver_name?: string;
  caregiver_email?: string;
  relationship_type?: string;
  is_primary_caregiver?: boolean;
}

export class SeniorModel {
  // 시니어 생성
  static async create(senior: Senior): Promise<Senior> {
    const query = `
      INSERT INTO seniors (user_id, name, birth_date, gender, address, emergency_contact, medical_history)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;
    
    const values = [
      senior.user_id,
      senior.name,
      senior.birth_date,
      senior.gender,
      senior.address,
      senior.emergency_contact,
      senior.medical_history
    ];

    const [result] = await pool.execute<ResultSetHeader>(query, values);
    
    // 생성된 시니어 조회
    const [rows] = await pool.execute<Senior[]>(
      'SELECT * FROM seniors WHERE id = ?',
      [result.insertId]
    );
    
    return rows[0];
  }

  // ID로 시니어 조회
  static async findById(id: number): Promise<Senior | null> {
    const [rows] = await pool.execute<Senior[]>(
      'SELECT * FROM seniors WHERE id = ?',
      [id]
    );
    return rows[0] || null;
  }

  // 사용자 ID로 시니어 조회
  static async findByUserId(userId: number): Promise<Senior | null> {
    const [rows] = await pool.execute<Senior[]>(
      'SELECT * FROM seniors WHERE user_id = ?',
      [userId]
    );
    return rows[0] || null;
  }

  // 보호자와 함께 시니어 조회
  static async findWithCaregivers(seniorId: number): Promise<SeniorWithCaregiver[]> {
    const query = `
      SELECT 
        s.*,
        u.display_name as caregiver_name,
        u.email as caregiver_email,
        csr.relationship_type,
        csr.is_primary_caregiver
      FROM seniors s
      JOIN caregiver_senior_relationships csr ON s.id = csr.senior_id
      JOIN users u ON csr.caregiver_id = u.id
      WHERE s.id = ?
      ORDER BY csr.is_primary_caregiver DESC, csr.created_at ASC
    `;
    
    const [rows] = await pool.execute<SeniorWithCaregiver[]>(query, [seniorId]);
    return rows;
  }

  // 보호자의 모든 시니어 조회
  static async findByCaregiverId(caregiverId: number): Promise<SeniorWithCaregiver[]> {
    const query = `
      SELECT 
        s.*,
        csr.relationship_type,
        csr.is_primary_caregiver
      FROM seniors s
      JOIN caregiver_senior_relationships csr ON s.id = csr.senior_id
      WHERE csr.caregiver_id = ?
      ORDER BY csr.is_primary_caregiver DESC, s.name ASC
    `;
    
    const [rows] = await pool.execute<SeniorWithCaregiver[]>(query, [caregiverId]);
    return rows;
  }

  // 시니어 정보 업데이트
  static async update(id: number, updates: Partial<Senior>): Promise<Senior | null> {
    const fields = Object.keys(updates).map(key => `${key} = ?`);
    const query = `
      UPDATE seniors 
      SET ${fields.join(', ')}
      WHERE id = ?
    `;
    
    const values = [...Object.values(updates), id];
    await pool.execute(query, values);
    
    // 업데이트된 시니어 조회
    return this.findById(id);
  }

  // 시니어 삭제
  static async delete(id: number): Promise<boolean> {
    const [result] = await pool.execute<ResultSetHeader>(
      'DELETE FROM seniors WHERE id = ?',
      [id]
    );
    return result.affectedRows > 0;
  }

  // 모든 시니어 조회 (관리자용)
  static async getAll(): Promise<Senior[]> {
    const [rows] = await pool.execute<Senior[]>(
      'SELECT * FROM seniors ORDER BY created_at DESC'
    );
    return rows;
  }

  // 보호자-시니어 관계 생성
  static async linkCaregiver(seniorId: number, caregiverId: number, relationshipType: string, isPrimary: boolean = false): Promise<boolean> {
    const query = `
      INSERT INTO caregiver_senior_relationships (senior_id, caregiver_id, relationship_type, is_primary_caregiver)
      VALUES (?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE 
        relationship_type = VALUES(relationship_type),
        is_primary_caregiver = VALUES(is_primary_caregiver)
    `;
    
    const [result] = await pool.execute<ResultSetHeader>(query, [seniorId, caregiverId, relationshipType, isPrimary]);
    return result.affectedRows > 0;
  }

  // 보호자-시니어 관계 삭제
  static async unlinkCaregiver(seniorId: number, caregiverId: number): Promise<boolean> {
    const [result] = await pool.execute<ResultSetHeader>(
      'DELETE FROM caregiver_senior_relationships WHERE senior_id = ? AND caregiver_id = ?',
      [seniorId, caregiverId]
    );
    return result.affectedRows > 0;
  }
}
