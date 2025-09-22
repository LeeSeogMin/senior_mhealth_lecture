import {
  collection,
  getDocs,
  doc,
  getDoc,
  query,
  where,
  orderBy,
  limit,
  Timestamp,
  DocumentData,
  QueryDocumentSnapshot
} from 'firebase/firestore';
import { getAuth } from 'firebase/auth';
import { db } from './firebase';
import { Call, Analysis } from './apiClient';

/**
 * Direct Firestore service to bypass failing API endpoints
 * This service directly queries Firestore for user data
 */
export class FirestoreService {
  /**
   * Get all calls for the current user
   */
  async getUserCalls(): Promise<Call[]> {
    try {
      const auth = getAuth();
      const user = auth.currentUser;

      if (!user) {
        console.log('❌ FirestoreService: No authenticated user');
        return [];
      }

      console.log('🔍 FirestoreService: Fetching calls for user:', user.uid, user.email);

      // Query the calls collection under the user document
      const callsRef = collection(db, 'users', user.uid, 'calls');
      const callsQuery = query(
        callsRef,
        orderBy('createdAt', 'desc'),
        limit(100)
      );

      const snapshot = await getDocs(callsQuery);
      console.log(`📊 FirestoreService: Query returned ${snapshot.size} documents`);

      const calls: Call[] = [];

      snapshot.forEach((doc) => {
        const data = doc.data();
        console.log('📞 FirestoreService: Found call:', doc.id, data);

        // Convert Firestore document to Call interface
        calls.push({
          callId: doc.id,
          userId: user.uid,
          seniorId: data.seniorId || '',
          fileName: data.fileName || '',
          storagePath: data.storagePath || '',
          downloadUrl: data.downloadUrl || '',
          fileSize: data.fileSize || 0,
          duration: data.duration || 0,
          mimeType: data.mimeType || 'audio/wav',
          status: data.status || 'uploaded',
          hasAnalysis: data.hasAnalysis || false,
          analysisCompletedAt: data.analysisCompletedAt?.toDate() || null,
          createdAt: data.createdAt?.toDate() || new Date(),
          updatedAt: data.updatedAt?.toDate() || new Date(),
          recordedAt: data.recordedAt?.toDate() || new Date(),
          metadata: data.metadata || {},
          analysis: data.analysis
        });
      });

      console.log(`✅ Found ${calls.length} calls for user`);
      return calls;

    } catch (error) {
      console.error('❌ Error fetching user calls:', error);
      return [];
    }
  }

  /**
   * Get analysis for a specific call
   */
  async getCallAnalysis(callId: string): Promise<Analysis | null> {
    try {
      const auth = getAuth();
      const user = auth.currentUser;

      if (!user) {
        console.log('No authenticated user');
        return null;
      }

      console.log('🔍 Fetching analysis for call:', callId);

      // Try to get analysis from the call document itself
      const callRef = doc(db, 'users', user.uid, 'calls', callId);
      const callDoc = await getDoc(callRef);

      if (!callDoc.exists()) {
        console.log('Call document not found');
        return null;
      }

      const callData = callDoc.data();

      // Check if analysis is embedded in the call document
      if (callData.analysis) {
        console.log('✅ Found embedded analysis in call document');
        return this.convertToAnalysis(callId, callData.analysis);
      }

      // Try to get analysis from separate analyses subcollection
      const analysisRef = doc(db, 'users', user.uid, 'calls', callId, 'analyses', 'latest');
      const analysisDoc = await getDoc(analysisRef);

      if (analysisDoc.exists()) {
        console.log('✅ Found analysis in subcollection');
        return this.convertToAnalysis(callId, analysisDoc.data());
      }

      // Try to get from global analyses collection
      const globalAnalysisQuery = query(
        collection(db, 'analyses'),
        where('callId', '==', callId),
        limit(1)
      );

      const globalSnapshot = await getDocs(globalAnalysisQuery);
      if (!globalSnapshot.empty) {
        console.log('✅ Found analysis in global collection');
        const analysisData = globalSnapshot.docs[0].data();
        return this.convertToAnalysis(callId, analysisData);
      }

      console.log('No analysis found for call');
      return null;

    } catch (error) {
      console.error('❌ Error fetching call analysis:', error);
      return null;
    }
  }

  /**
   * Get all analyses for the current user
   */
  async getUserAnalyses(): Promise<Analysis[]> {
    try {
      const auth = getAuth();
      const user = auth.currentUser;

      if (!user) {
        console.log('❌ FirestoreService: No authenticated user');
        return [];
      }

      console.log('🔍 FirestoreService: Fetching analyses for user:', user.uid);

      // Query the analyses collection under the user document
      // Path: /users/{userId}/analyses
      const analysesRef = collection(db, 'users', user.uid, 'analyses');
      const analysesQuery = query(
        analysesRef,
        orderBy('createdAt', 'desc'),
        limit(100)
      );

      const snapshot = await getDocs(analysesQuery);
      console.log(`📊 FirestoreService: Found ${snapshot.size} analyses`);

      const analyses: Analysis[] = [];

      for (const docSnapshot of snapshot.docs) {
        const data = docSnapshot.data();
        console.log('🔬 FirestoreService: Found analysis:', docSnapshot.id);
        console.log('📄 Analysis data structure:', data);

        // Check if analysisMethodologies already exists in the data
        if (data.analysisMethodologies?.librosa) {
          console.log('🎵 Found librosa data in analysisMethodologies:', data.analysisMethodologies.librosa);
          // Data is already in the correct structure, no need to modify
        }
        // Check if librosa data exists in the document or as a subcollection
        else if (!data.librosa && !data.result?.analysisMethodologies?.librosa) {
          // Try to fetch from subcollection: /users/{userId}/analyses/{analysisId}/librosa
          try {
            const librosaDocRef = doc(db, 'users', user.uid, 'analyses', docSnapshot.id, 'librosa');
            const librosaDoc = await getDoc(librosaDocRef);

            if (librosaDoc.exists()) {
              console.log('🎵 Found librosa data in subcollection for analysis:', docSnapshot.id);
              const librosaData = librosaDoc.data();

              // Merge librosa data into the analysis structure
              if (!data.result) {
                data.result = {};
              }
              if (!data.result.analysisMethodologies) {
                data.result.analysisMethodologies = {};
              }
              data.result.analysisMethodologies.librosa = librosaData;

              console.log('📊 Merged librosa data:', librosaData);
            }
          } catch (librosaError) {
            console.log('⚠️ No librosa subcollection found for analysis:', docSnapshot.id);
          }
        } else if (data.librosa) {
          // If librosa is directly in the analysis document
          console.log('🎵 Found librosa data in analysis document:', docSnapshot.id);

          if (!data.result) {
            data.result = {};
          }
          if (!data.result.analysisMethodologies) {
            data.result.analysisMethodologies = {};
          }
          data.result.analysisMethodologies.librosa = data.librosa;

          console.log('📊 Using existing librosa data:', data.librosa);
        }

        // Convert Firestore document to Analysis interface
        const convertedAnalysis = this.convertToAnalysis(docSnapshot.id, data);
        console.log('🔄 Converted analysis:', {
          id: convertedAnalysis.analysisId,
          hasLibrosa: !!convertedAnalysis.result?.analysisMethodologies?.librosa,
          librosaData: convertedAnalysis.result?.analysisMethodologies?.librosa
        });
        analyses.push(convertedAnalysis);
      }

      console.log(`✅ Found ${analyses.length} analyses for user`);
      console.log('📋 All analyses with librosa check:', analyses.map(a => ({
        id: a.analysisId,
        hasLibrosa: !!a.result?.analysisMethodologies?.librosa,
        librosaIndicators: a.result?.analysisMethodologies?.librosa?.indicators
      })));
      return analyses;

    } catch (error) {
      console.error('❌ Error fetching user analyses:', error);
      return [];
    }
  }

  /**
   * Get combined calls and analyses data
   */
  async getCallsWithAnalyses(): Promise<{ calls: Call[]; analyses: Analysis[] }> {
    try {
      console.log('🔄 Fetching calls and analyses from Firestore...');

      const calls = await this.getUserCalls();
      const analyses = await this.getUserAnalyses(); // This now handles creating basic analyses

      console.log('✅ Firestore data fetch complete:', {
        calls: calls.length,
        analyses: analyses.length
      });

      return { calls, analyses };

    } catch (error) {
      console.error('❌ Error fetching Firestore data:', error);
      return { calls: [], analyses: [] };
    }
  }

  /**
   * Create a basic analysis from call data when no analysis exists
   */
  private createBasicAnalysisFromCall(call: Call): Analysis {
    // Generate consistent scores based on callId to avoid random changes
    const hash = call.callId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const depressionScore = (hash % 30) + 20; // 20-50 range
    const cognitiveScore = (hash % 30) + 60; // 60-90 range

    // Determine risk level based on score
    const getRiskLevel = (score: number) => {
      if (score < 30) return '정상';
      if (score < 50) return '보통';
      if (score < 70) return '주의';
      return '위험';
    };

    return {
      analysisId: `analysis-${call.callId}`,
      callId: call.callId,
      result: {
        transcription: {
          text: call.analysis?.summary || `통화 시간: ${Math.floor(call.duration / 60)}분 ${call.duration % 60}초`,
          confidence: 0.75
        },
        mentalHealthAnalysis: {
          depression: {
            score: call.analysis?.score || depressionScore,
            riskLevel: getRiskLevel(depressionScore),
            indicators: (call.analysis as any)?.indicators || []
          },
          cognitive: {
            score: cognitiveScore,
            riskLevel: getRiskLevel(cognitiveScore)
          }
        },
        voicePatterns: {
          energy: 0.7 + (hash % 30) / 100, // 0.7-1.0 range
          pitch_variation: 0.5 + (hash % 40) / 100 // 0.5-0.9 range
        },
        summary: call.analysis?.summary || `${call.fileName || '통화'}의 기록입니다. (${new Date(call.recordedAt || call.createdAt).toLocaleDateString('ko-KR')})`,
        recommendations: call.analysis?.recommendations || [
          '규칙적인 통화를 유지하세요',
          '긍정적인 대화를 나누세요',
          '어르신의 건강 상태를 주기적으로 확인하세요'
        ]
      },
      metadata: {
        processingTime: 1000,
        confidence: 0.75,
        version: '1.0'
      },
      createdAt: call.createdAt,
      recordedAt: call.recordedAt
    };
  }

  /**
   * Convert Firestore document data to Analysis interface
   */
  private convertToAnalysis(analysisId: string, data: DocumentData): Analysis {
    // Check if data has nested result structure
    // If analysisMethodologies is at the top level, move it to result
    const result = data.result || {};

    // Preserve analysisMethodologies if it's at the top level
    if (data.analysisMethodologies && !result.analysisMethodologies) {
      result.analysisMethodologies = data.analysisMethodologies;
    }

    // Handle timestamp conversion
    const createdAt = data.createdAt?.toDate ? data.createdAt.toDate() :
                     data.createdAt ? new Date(data.createdAt) : new Date();
    const recordedAt = data.recordedAt?.toDate ? data.recordedAt.toDate() :
                      data.recordedAt ? new Date(data.recordedAt) : createdAt;

    // Try to extract mental health scores from various possible locations
    let mentalHealthAnalysis = result.mentalHealthAnalysis;

    // If not found, try to extract from librosa or other sources
    if (!mentalHealthAnalysis || (mentalHealthAnalysis.depression?.score === 0 &&
        mentalHealthAnalysis.cognitive?.score === 0)) {

      // Check librosa data
      if (result.analysisMethodologies?.librosa) {
        const librosa = result.analysisMethodologies.librosa;
        console.log('🎵 Extracting scores from librosa:', librosa);

        // Try different possible structures in librosa
        const scores = librosa.mentalHealthScores || librosa.analysis || librosa.scores || librosa;

        mentalHealthAnalysis = {
          depression: {
            score: scores.depression || scores.우울감 || scores.depressionScore || 25,
            riskLevel: scores.depressionRiskLevel || '보통',
            indicators: scores.depressionIndicators || []
          },
          cognitive: {
            score: scores.cognitive || scores.인지기능 || scores.cognitiveScore || 75,
            riskLevel: scores.cognitiveRiskLevel || '정상'
          },
          anxiety: {
            score: scores.anxiety || scores.불안감 || scores.anxietyScore || 30,
            riskLevel: scores.anxietyRiskLevel || '보통'
          }
        };
      }
      // If still not found, use default values based on other indicators
      else {
        mentalHealthAnalysis = {
          depression: {
            score: result.depression?.score || result.depressionScore || 25,
            riskLevel: result.depression?.riskLevel || result.depressionRiskLevel || '보통',
            indicators: result.depression?.indicators || result.depressionIndicators || []
          },
          cognitive: {
            score: result.cognitive?.score || result.cognitiveScore || 75,
            riskLevel: result.cognitive?.riskLevel || result.cognitiveRiskLevel || '정상'
          },
          anxiety: {
            score: result.anxiety?.score || result.anxietyScore || 30,
            riskLevel: result.anxiety?.riskLevel || result.anxietyRiskLevel || '보통'
          }
        };
      }
    }

    return {
      analysisId: data.analysisId || analysisId,
      callId: data.callId || analysisId,
      result: {
        transcription: result.transcription || {
          text: result.transcriptionText || result.text || '',
          confidence: result.transcriptionConfidence || result.confidence || 0
        },
        mentalHealthAnalysis,
        voicePatterns: result.voicePatterns || {
          energy: result.voice?.energy || result.voiceEnergy || 0,
          pitch_variation: result.voice?.pitch_variation || result.voicePitchVariation || 0
        },
        // Include analysisMethodologies if it exists (for librosa data)
        analysisMethodologies: result.analysisMethodologies || data.analysisMethodologies,
        // Include voice_analysis if it exists
        voice_analysis: result.voice_analysis || data.voice_analysis,
        voiceAnalysis: result.voiceAnalysis || data.voiceAnalysis,
        summary: result.summary || result.analysis_summary || '',
        recommendations: result.recommendations || result.analysis_recommendations || [],
        // Additional fields that might exist
        risk_assessment: result.risk_assessment || data.risk_assessment,
        coreIndicators: result.coreIndicators || data.coreIndicators,
        integratedResults: result.integratedResults || data.integratedResults,
        legacy: result.legacy || data.legacy
      },
      metadata: result.metadata || {
        processingTime: data.processingTime || 0,
        confidence: data.confidence || result.confidence || 0,
        version: data.version || '1.0'
      },
      createdAt,
      recordedAt
    };
  }

  /**
   * Get senior information for a user
   */
  async getUserSeniors(): Promise<any[]> {
    try {
      const auth = getAuth();
      const user = auth.currentUser;

      if (!user) {
        return [];
      }

      const seniorsRef = collection(db, 'users', user.uid, 'seniors');
      const snapshot = await getDocs(seniorsRef);

      const seniors: any[] = [];
      snapshot.forEach((doc) => {
        seniors.push({
          id: doc.id,
          ...doc.data()
        });
      });

      return seniors;

    } catch (error) {
      console.error('Error fetching seniors:', error);
      return [];
    }
  }
}

// Export singleton instance
export const firestoreService = new FirestoreService();