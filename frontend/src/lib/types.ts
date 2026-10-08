export type StudyStatus = "UPLOADED" | "PROCESSING" | "DONE" | "FAILED";

export interface Study {
  id: string;
  name: string;
  status: StudyStatus;
  sequences_present: Record<string, boolean>;
  qc_flags: Record<string, string>;
  created_at: string;
  owner_user_id?: number | null;
}

export interface FileArtifact {
  id: number;
  kind:
    | "T1"
    | "T1CE"
    | "T2"
    | "FLAIR"
    | "NIFTI"
    | "DICOM_ZIP"
    | "SEG_NIFTI"
    | "SEG_DICOM"
    | "PDF"
    | "JSON"
    | "STL"
    | "PNG";
  path: string;
  size_bytes: number;
  checksum: string;
  created_at: string;
}

export interface Metrics {
  wt_ml: number;
  tc_ml: number;
  et_ml: number;
  edema_core_ratio: number;
  confidence_summary: number;
  low_confidence_fraction: number;
  model_agreement_wt_dice?: number | null;
  label_disagreement_ml?: number | null;
  runtime_sec: number;
  created_at: string;
}

export interface Comparison {
  id: number;
  study_a_id: string;
  study_b_id: string;
  volume_a_ml: number;
  volume_b_ml: number;
  pct_change: number;
  rano_label: string;
  created_at: string;
}

export interface UserAuth {
  token?: {
    access_token: string;
    token_type: string;
    expires_at: string;
  };
  user?: {
    id: number;
    email: string;
    created_at: string;
  };
}
