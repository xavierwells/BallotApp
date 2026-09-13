export type SectionChoice = "accepted" | "flagged";
export type EditableSection = {
  key: string; ballotTitle: string;
  candidates: { ballotLabel: string; partyLabel: string }[];
};
export type SectionDraft = {
  decision: SectionChoice; note: string; editing: boolean; edits: Record<string, string>;
  decisionBeforeEdit?: SectionChoice;
};
export type FieldCorrection = {
  field: "ballotTitle" | "ballotLabel" | "partyLabel"; candidateIndex?: number; value: string;
};

export function editTranscription(
  race: EditableSection, draft: SectionDraft | undefined, field: string, value: string,
  savedDecision?: { decision: string; note: string },
): SectionDraft | undefined {
  // A field change must never implicitly choose Flag for the reviewer.
  if ((draft?.decision ?? savedDecision?.decision) !== "flagged") return draft;
  const edits = { ...draft?.edits, [field]: value };
  // Keep raw text while typing (including spaces); normalize only on blur/save.
  const [name, rawIndex] = field.split(":");
  const original = field === "ballotTitle" ? race.ballotTitle :
    (name === "ballotLabel" || name === "partyLabel") ? race.candidates[Number(rawIndex)]?.[name] : undefined;
  if (original === undefined) throw new Error("Unknown correction field.");
  if (value === original) delete edits[field];
  const decisionBeforeEdit = draft?.editing ? draft.decisionBeforeEdit : draft?.decision;
  if (!Object.keys(edits).length) {
    // Reverting text restores an explicit unsaved choice, not a new approval.
    if (decisionBeforeEdit || draft?.note.trim()) return {
      decision: decisionBeforeEdit ?? "flagged", note: draft?.note ?? "", editing: false, edits: {},
    };
    return undefined;
  }
  return { decision: "flagged", note: draft?.note ?? savedDecision?.note ?? "", editing: true, edits, decisionBeforeEdit };
}

export function fieldCorrections(race: EditableSection, draft: SectionDraft): FieldCorrection[] {
  const result: FieldCorrection[] = [];
  if (draft.decision !== "flagged" || !draft.editing) return result;
  for (const [key, proposed] of Object.entries(draft.edits)) {
    const value = proposed.trim();
    if (key === "ballotTitle") {
      if (value !== race.ballotTitle) result.push({ field: "ballotTitle", value });
      continue;
    }
    const [field, rawIndex] = key.split(":");
    const candidateIndex = Number(rawIndex);
    if ((field !== "ballotLabel" && field !== "partyLabel") || !Number.isInteger(candidateIndex) || !race.candidates[candidateIndex]) {
      throw new Error("Unknown correction field.");
    }
    if (value !== race.candidates[candidateIndex][field]) result.push({ field, candidateIndex, value });
  }
  return result;
}

export function sectionSubmission(races: EditableSection[], drafts: Record<string, SectionDraft>) {
  return Object.entries(drafts).map(([raceKey, draft]) => {
    const race = races.find(item => item.key === raceKey);
    if (!race) throw new Error("This section is no longer in the draft. Reload the review task.");
    const corrections = fieldCorrections(race, draft);
    if (corrections.some(c => !c.value || c.value.length > 255)) throw new Error("Corrected labels must contain 1–255 characters.");
    if (draft.decision === "flagged" && !draft.note.trim() && !corrections.length) {
      throw new Error(`Add a note or a transcription correction for ${race.ballotTitle}.`);
    }
    return { raceKey, decision: draft.decision, note: draft.decision === "flagged" ? draft.note.trim() : "", corrections };
  });
}
