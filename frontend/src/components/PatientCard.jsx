import Panel from "./Panel.jsx";

const FIELDS = [
  ["patient_name", "Name"],
  ["situation", "What happened"],
  ["pain_location", "Pain"],
  ["temperature", "Temperature"],
  ["medical_conditions", "Conditions"],
  ["medications", "Medications"],
  ["allergies", "Allergies"],
  ["alcohol_consumed", "Alcohol"],
  ["notes", "Notes"],
];

export default function PatientCard({ patient }) {
  return (
    <Panel title="Patient record">
      {!patient ? (
        <div className="text-xs italic text-muted">
          Not collected yet — fills in at dispatch.
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          {FIELDS.map(([k, label]) => {
            const v = (patient[k] || "").trim();
            if (!v) return null;
            return (
              <div key={k} className="flex justify-between gap-3 text-xs">
                <span className="shrink-0 text-muted">{label}</span>
                <span className="text-right text-ink">{v}</span>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}
