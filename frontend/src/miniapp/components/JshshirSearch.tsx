import { useState } from "react";
import { isValidJshshir, sanitizeJshshirInput } from "../utils/passport";
import { MainButton, Section, TextField } from "./ui";

/** JShShIR kiritish formasi — davomatdan olib tashlash va chetlatish uchun umumiy. */
export function JshshirSearch({
  initial = "",
  loading,
  footer,
  onSearch,
}: {
  initial?: string;
  loading: boolean;
  footer: string;
  onSearch: (jshshir: string) => void;
}) {
  const [value, setValue] = useState(initial);
  const [touched, setTouched] = useState(false);
  const valid = isValidJshshir(value);

  const submit = () => {
    setTouched(true);
    if (valid && !loading) onSearch(value);
  };

  return (
    <>
      <Section footer={footer}>
        <TextField
          label="JShShIR (PINFL)"
          value={value}
          onChange={(v) => setValue(sanitizeJshshirInput(v))}
          placeholder="14 ta raqam"
          inputMode="numeric"
          hint={`${value.length}/14`}
          error={touched && !valid ? "JShShIR 14 ta raqamdan iborat bo'lishi kerak" : null}
          onEnter={submit}
        />
      </Section>
      <MainButton text="Qidirish" onClick={submit} disabled={!valid} loading={loading} />
    </>
  );
}
