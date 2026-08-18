import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const FIRST_NAMES_M = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark"];
const FIRST_NAMES_F = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra"];
const LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"];

export function getPatientName(patientId: string, gender: string = "F") {
  let hash = 0;
  for (let i = 0; i < patientId.length; i++) {
    hash = patientId.charCodeAt(i) + ((hash << 5) - hash);
  }
  hash = Math.abs(hash);
  const firstNames = gender === "M" ? FIRST_NAMES_M : FIRST_NAMES_F;
  const firstName = firstNames[hash % firstNames.length];
  const lastName = LAST_NAMES[(hash >> 4) % LAST_NAMES.length];
  return `${firstName} ${lastName}`;
}

