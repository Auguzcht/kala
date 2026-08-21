export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.15"
  }
  public: {
    Tables: {
      assessments: {
        Row: {
          course_id: string
          created_at: string
          id: string
          institution_id: string
          lms_ref: string | null
          skill_id: string | null
          title: string | null
        }
        Insert: {
          course_id: string
          created_at?: string
          id?: string
          institution_id: string
          lms_ref?: string | null
          skill_id?: string | null
          title?: string | null
        }
        Update: {
          course_id?: string
          created_at?: string
          id?: string
          institution_id?: string
          lms_ref?: string | null
          skill_id?: string | null
          title?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "assessments_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "assessments_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "assessments_skill_id_fkey"
            columns: ["skill_id"]
            isOneToOne: false
            referencedRelation: "skills"
            referencedColumns: ["id"]
          },
        ]
      }
      audit_log: {
        Row: {
          action: string
          actor_id: string | null
          actor_role: string | null
          id: number
          institution_id: string | null
          metadata: Json | null
          new_data: Json | null
          occurred_at: string
          old_data: Json | null
          row_id: string | null
          table_name: string | null
        }
        Insert: {
          action: string
          actor_id?: string | null
          actor_role?: string | null
          id?: never
          institution_id?: string | null
          metadata?: Json | null
          new_data?: Json | null
          occurred_at?: string
          old_data?: Json | null
          row_id?: string | null
          table_name?: string | null
        }
        Update: {
          action?: string
          actor_id?: string | null
          actor_role?: string | null
          id?: never
          institution_id?: string | null
          metadata?: Json | null
          new_data?: Json | null
          occurred_at?: string
          old_data?: Json | null
          row_id?: string | null
          table_name?: string | null
        }
        Relationships: []
      }
      consents: {
        Row: {
          created_at: string
          granted: boolean
          id: string
          institution_id: string
          policy_version: string
          purpose: string
          user_id: string
        }
        Insert: {
          created_at?: string
          granted: boolean
          id?: string
          institution_id: string
          policy_version: string
          purpose?: string
          user_id: string
        }
        Update: {
          created_at?: string
          granted?: boolean
          id?: string
          institution_id?: string
          policy_version?: string
          purpose?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "consents_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "consents_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      content_items: {
        Row: {
          chunk_text: string | null
          course_id: string
          created_at: string
          embedding: string | null
          id: string
          institution_id: string
          lms_ref: string | null
          skill_id: string | null
        }
        Insert: {
          chunk_text?: string | null
          course_id: string
          created_at?: string
          embedding?: string | null
          id?: string
          institution_id: string
          lms_ref?: string | null
          skill_id?: string | null
        }
        Update: {
          chunk_text?: string | null
          course_id?: string
          created_at?: string
          embedding?: string | null
          id?: string
          institution_id?: string
          lms_ref?: string | null
          skill_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "content_items_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "content_items_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "content_items_skill_id_fkey"
            columns: ["skill_id"]
            isOneToOne: false
            referencedRelation: "skills"
            referencedColumns: ["id"]
          },
        ]
      }
      courses: {
        Row: {
          created_at: string
          id: string
          institution_id: string
          lms_course_id: string
          title: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          id?: string
          institution_id: string
          lms_course_id: string
          title: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          id?: string
          institution_id?: string
          lms_course_id?: string
          title?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "courses_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
        ]
      }
      data_subject_requests: {
        Row: {
          id: string
          institution_id: string
          kind: string
          requested_at: string
          resolved_at: string | null
          status: string
          user_id: string
        }
        Insert: {
          id?: string
          institution_id: string
          kind: string
          requested_at?: string
          resolved_at?: string | null
          status?: string
          user_id: string
        }
        Update: {
          id?: string
          institution_id?: string
          kind?: string
          requested_at?: string
          resolved_at?: string | null
          status?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "data_subject_requests_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "data_subject_requests_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      enrollments: {
        Row: {
          course_id: string
          created_at: string
          institution_id: string
          role: string
          user_id: string
        }
        Insert: {
          course_id: string
          created_at?: string
          institution_id: string
          role: string
          user_id: string
        }
        Update: {
          course_id?: string
          created_at?: string
          institution_id?: string
          role?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "enrollments_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "enrollments_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "enrollments_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      evidence_events: {
        Row: {
          correct: boolean | null
          course_id: string
          created_at: string
          hints_used: number
          id: string
          institution_id: string
          latency_ms: number | null
          skill_id: string | null
          type: string
          user_id: string
        }
        Insert: {
          correct?: boolean | null
          course_id: string
          created_at?: string
          hints_used?: number
          id?: string
          institution_id: string
          latency_ms?: number | null
          skill_id?: string | null
          type: string
          user_id: string
        }
        Update: {
          correct?: boolean | null
          course_id?: string
          created_at?: string
          hints_used?: number
          id?: string
          institution_id?: string
          latency_ms?: number | null
          skill_id?: string | null
          type?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "evidence_events_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_events_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_events_skill_id_fkey"
            columns: ["skill_id"]
            isOneToOne: false
            referencedRelation: "skills"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_events_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      institutions: {
        Row: {
          created_at: string
          deployment_id: string
          id: string
          lms_issuer: string
          lms_type: string
          name: string
          region: string | null
          updated_at: string
        }
        Insert: {
          created_at?: string
          deployment_id: string
          id?: string
          lms_issuer: string
          lms_type: string
          name: string
          region?: string | null
          updated_at?: string
        }
        Update: {
          created_at?: string
          deployment_id?: string
          id?: string
          lms_issuer?: string
          lms_type?: string
          name?: string
          region?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      lti_launches: {
        Row: {
          course_id: string | null
          id: string
          institution_id: string
          ip: unknown
          message_type: string | null
          occurred_at: string
          role: string | null
          user_agent: string | null
          user_id: string | null
        }
        Insert: {
          course_id?: string | null
          id?: string
          institution_id: string
          ip?: unknown
          message_type?: string | null
          occurred_at?: string
          role?: string | null
          user_agent?: string | null
          user_id?: string | null
        }
        Update: {
          course_id?: string | null
          id?: string
          institution_id?: string
          ip?: unknown
          message_type?: string | null
          occurred_at?: string
          role?: string | null
          user_agent?: string | null
          user_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "lti_launches_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "lti_launches_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      mastery_state: {
        Row: {
          attempts: number
          course_id: string
          estimate: number
          institution_id: string
          last_seen: string | null
          skill_id: string
          updated_at: string
          user_id: string
        }
        Insert: {
          attempts?: number
          course_id: string
          estimate?: number
          institution_id: string
          last_seen?: string | null
          skill_id: string
          updated_at?: string
          user_id: string
        }
        Update: {
          attempts?: number
          course_id?: string
          estimate?: number
          institution_id?: string
          last_seen?: string | null
          skill_id?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "mastery_state_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "mastery_state_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "mastery_state_skill_id_fkey"
            columns: ["skill_id"]
            isOneToOne: false
            referencedRelation: "skills"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "mastery_state_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      readiness_snapshots: {
        Row: {
          course_id: string
          created_at: string
          id: string
          institution_id: string
          score: number
          user_id: string
        }
        Insert: {
          course_id: string
          created_at?: string
          id?: string
          institution_id: string
          score: number
          user_id: string
        }
        Update: {
          course_id?: string
          created_at?: string
          id?: string
          institution_id?: string
          score?: number
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "readiness_snapshots_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "readiness_snapshots_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "readiness_snapshots_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      recommendations: {
        Row: {
          action: string
          course_id: string
          created_at: string
          id: string
          institution_id: string
          rationale: string | null
          skill_id: string | null
          user_id: string
        }
        Insert: {
          action: string
          course_id: string
          created_at?: string
          id?: string
          institution_id: string
          rationale?: string | null
          skill_id?: string | null
          user_id: string
        }
        Update: {
          action?: string
          course_id?: string
          created_at?: string
          id?: string
          institution_id?: string
          rationale?: string | null
          skill_id?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "recommendations_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "recommendations_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "recommendations_skill_id_fkey"
            columns: ["skill_id"]
            isOneToOne: false
            referencedRelation: "skills"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "recommendations_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: false
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      researcher_grants: {
        Row: {
          created_at: string
          expires_at: string
          granted_by: string | null
          id: string
          institution_id: string
          researcher_id: string
          scope: string
          status: string
        }
        Insert: {
          created_at?: string
          expires_at: string
          granted_by?: string | null
          id?: string
          institution_id: string
          researcher_id: string
          scope?: string
          status?: string
        }
        Update: {
          created_at?: string
          expires_at?: string
          granted_by?: string | null
          id?: string
          institution_id?: string
          researcher_id?: string
          scope?: string
          status?: string
        }
        Relationships: [
          {
            foreignKeyName: "researcher_grants_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "researcher_grants_researcher_id_fkey"
            columns: ["researcher_id"]
            isOneToOne: false
            referencedRelation: "researchers"
            referencedColumns: ["id"]
          },
        ]
      }
      researchers: {
        Row: {
          created_at: string
          display_name: string | null
          email: string
          id: string
        }
        Insert: {
          created_at?: string
          display_name?: string | null
          email: string
          id?: string
        }
        Update: {
          created_at?: string
          display_name?: string | null
          email?: string
          id?: string
        }
        Relationships: []
      }
      skills: {
        Row: {
          bloom_level: string
          blueprint_weight: number
          course_id: string
          created_at: string
          id: string
          institution_id: string
          name: string
        }
        Insert: {
          bloom_level: string
          blueprint_weight?: number
          course_id: string
          created_at?: string
          id?: string
          institution_id: string
          name: string
        }
        Update: {
          bloom_level?: string
          blueprint_weight?: number
          course_id?: string
          created_at?: string
          id?: string
          institution_id?: string
          name?: string
        }
        Relationships: [
          {
            foreignKeyName: "skills_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "skills_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
        ]
      }
      user_profiles: {
        Row: {
          display_name: string | null
          email: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          display_name?: string | null
          email?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          display_name?: string | null
          email?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_profiles_user_id_fkey"
            columns: ["user_id"]
            isOneToOne: true
            referencedRelation: "users"
            referencedColumns: ["id"]
          },
        ]
      }
      users: {
        Row: {
          created_at: string
          id: string
          institution_id: string
          lms_user_id: string
          pseudonym: string
          role: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          id?: string
          institution_id: string
          lms_user_id: string
          pseudonym: string
          role: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          id?: string
          institution_id?: string
          lms_user_id?: string
          pseudonym?: string
          role?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "users_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      research_cohort_daily: {
        Row: {
          attempts: number | null
          bloom_level: string | null
          correct: number | null
          course_id: string | null
          day: string | null
          institution_id: string | null
        }
        Relationships: [
          {
            foreignKeyName: "evidence_events_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_events_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
        ]
      }
      research_evidence_anon: {
        Row: {
          correct: boolean | null
          course_id: string | null
          created_at: string | null
          hints_used: number | null
          institution_id: string | null
          latency_ms: number | null
          skill_id: string | null
          subject: string | null
          type: string | null
        }
        Relationships: [
          {
            foreignKeyName: "evidence_events_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_events_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "evidence_events_skill_id_fkey"
            columns: ["skill_id"]
            isOneToOne: false
            referencedRelation: "skills"
            referencedColumns: ["id"]
          },
        ]
      }
      research_mastery_anon: {
        Row: {
          attempts: number | null
          bloom_level: string | null
          course_id: string | null
          estimate: number | null
          institution_id: string | null
          skill: string | null
          subject: string | null
          updated_at: string | null
        }
        Relationships: [
          {
            foreignKeyName: "mastery_state_course_id_fkey"
            columns: ["course_id"]
            isOneToOne: false
            referencedRelation: "courses"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "mastery_state_institution_id_fkey"
            columns: ["institution_id"]
            isOneToOne: false
            referencedRelation: "institutions"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Functions: {
      current_app_role: { Args: never; Returns: string }
      current_institution: { Args: never; Returns: string }
      has_consent: { Args: { subject: string }; Returns: boolean }
      has_grant: { Args: { inst: string }; Returns: boolean }
      is_admin: { Args: never; Returns: boolean }
      is_staff: { Args: never; Returns: boolean }
      match_content_items: {
        Args: {
          p_course_id: string
          p_institution_id: string
          p_match_count?: number
          p_query: string
        }
        Returns: {
          chunk_text: string
          id: string
          similarity: number
          skill_id: string
        }[]
      }
      teaches: { Args: { course: string }; Returns: boolean }
      user_institution: { Args: { u: string }; Returns: string }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
