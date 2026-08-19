import { useSyncExternalStore } from "react";
import {
  patients as seed,
  type Patient,
  type PatientStatus,
  type CareAssessmentRecord,
} from "./mock-data";

let state: Patient[] = seed;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export function setPatientStatus(id: string, status: PatientStatus, nextAction?: string) {
  state = state.map((p) =>
    p.id === id
      ? {
          ...p,
          status,
          lastContact: "Aug 16, 2026",
          nextAction: nextAction ?? p.nextAction ?? "Await patient response",
        }
      : p,
  );
  emit();
}

export function addCareAssessment(assessment: CareAssessmentRecord) {
  state = state.map((p) => {
    if (
      p.id.toLowerCase() === assessment.patient_id.toLowerCase() ||
      p.mrn.toLowerCase() === assessment.patient_id.toLowerCase()
    ) {
      const existing = p.assessments || [];
      return {
        ...p,
        assessments: [assessment, ...existing],
        lastContact: "Aug 16, 2026",
      };
    }
    return p;
  });
  emit();
}

export function findPatientByIdOrMrn(query: string): Patient | undefined {
  if (!query) return undefined;
  const q = query.trim().toLowerCase();
  const cleanQ = q.replace(/[^a-z0-9]/g, "");
  return state.find((p) => {
    const idClean = p.id.toLowerCase().replace(/[^a-z0-9]/g, "");
    const mrnClean = p.mrn.toLowerCase().replace(/[^a-z0-9]/g, "");
    return (
      p.id.toLowerCase() === q ||
      p.mrn.toLowerCase() === q ||
      idClean === cleanQ ||
      mrnClean === cleanQ ||
      p.name.toLowerCase().includes(q)
    );
  });
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function getSnapshot() {
  return state;
}

export function usePatients() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export function usePatient(id: string) {
  if (!id) return undefined;
  return usePatients().find(
    (p) =>
      p.id.toLowerCase() === id.toLowerCase() ||
      p.mrn.toLowerCase() === id.toLowerCase() ||
      p.id.toLowerCase().replace(/[^a-z0-9]/g, "") === id.toLowerCase().replace(/[^a-z0-9]/g, ""),
  );
}
