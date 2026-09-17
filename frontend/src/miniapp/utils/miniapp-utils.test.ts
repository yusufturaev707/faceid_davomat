import { describe, expect, it } from "vitest";
import { errorMessage } from "../api";
import { resolveInitialRegion } from "../context";
import type { SmenaInfo } from "../types";
import { attendancePercent, formatDay, formatWeekday, groupSmenasByDay, sumCounts } from "./format";
import {
  isValidJshshir,
  looksLikeIdCardQr,
  parsePassport,
  sanitizeJshshirInput,
  sanitizePassportInput,
} from "./passport";

describe("passport", () => {
  it("seriya va raqamni bitta qatordan ajratadi", () => {
    expect(parsePassport("AD2311141")).toEqual({ ps_ser: "AD", ps_num: "2311141" });
    expect(parsePassport("ad-2311141")).toEqual({ ps_ser: "AD", ps_num: "2311141" });
    expect(parsePassport("AD 231 1141")).toEqual({ ps_ser: "AD", ps_num: "2311141" });
  });

  it("kirillcha lookalike harflarni lotinga o'giradi", () => {
    expect(parsePassport("АД2311141")).toEqual({ ps_ser: "AD", ps_num: "2311141" });
    expect(parsePassport("ас2311141")).toEqual({ ps_ser: "AC", ps_num: "2311141" });
  });

  it("noto'g'ri formatni rad etadi", () => {
    expect(parsePassport("A2311141")).toBeNull();
    expect(parsePassport("AD231114")).toBeNull();
    expect(parsePassport("AD23111412")).toBeNull();
    expect(parsePassport("12AD34567")).toBeNull();
  });

  it("kiritish maydonini tozalaydi", () => {
    expect(sanitizePassportInput("ad-23 11141999")).toBe("AD2311141");
    expect(sanitizeJshshirInput("123 456-78901234 99")).toBe("12345678901234");
  });

  it("JShShIR aynan 14 ta raqam", () => {
    expect(isValidJshshir("12345678901234")).toBe(true);
    expect(isValidJshshir("1234567890123")).toBe(false);
    expect(isValidJshshir("1234567890123a")).toBe(false);
  });

  it("ID-karta QR (MRZ) matnini taniydi", () => {
    expect(looksLikeIdCardQr("IUUZBAD12345674123456789012342<<<<")).toBe(true);
    expect(looksLikeIdCardQr("https://example.com/qr")).toBe(false);
  });
});

describe("format", () => {
  it("sanani vaqt zonasiz o'zbekcha formatlaydi", () => {
    expect(formatDay("2026-05-11")).toBe("11-may, 2026");
    expect(formatDay("2026-01-01")).toBe("1-yanvar, 2026");
    expect(formatWeekday("2026-05-11")).toBe("Dushanba");
  });

  it("davomat foizini bir xonagacha hisoblaydi", () => {
    expect(attendancePercent({ total: 450, entered: 8 })).toBe(1.8);
    expect(attendancePercent({ total: 0, entered: 0 })).toBe(0);
    expect(attendancePercent({ total: 3, entered: 3 })).toBe(100);
  });

  it("regionlar yig'indisini hisoblaydi", () => {
    expect(
      sumCounts([
        { total: 10, entered: 4, not_entered: 6, cheating: 1 },
        { total: 5, entered: 5, not_entered: 0, cheating: 0 },
      ]),
    ).toEqual({ total: 15, entered: 9, not_entered: 6, cheating: 1 });
  });

  it("smenalarni kun bo'yicha tartibni saqlab guruhlaydi", () => {
    const smena = (id: number, day: string): SmenaInfo => ({
      id,
      smena_id: id,
      smena_number: id,
      smena_name: `${id}-Smena`,
      day,
    });
    const groups = groupSmenasByDay([
      smena(1, "2026-05-11"),
      smena(2, "2026-05-11"),
      smena(3, "2026-05-12"),
    ]);
    expect(groups.map((g) => [g.day, g.smenas.map((s) => s.id)])).toEqual([
      ["2026-05-11", [1, 2]],
      ["2026-05-12", [3]],
    ]);
  });
});

describe("resolveInitialRegion", () => {
  const regions = [
    { id: 12, name: "Sirdaryo viloyati", number: 12 },
    { id: 14, name: "Toshkent shahri", number: 14 },
  ];

  it("yagona viloyatni avtomatik tanlaydi", () => {
    expect(resolveInitialRegion([regions[0]], null)).toEqual(regions[0]);
  });

  it("saqlangan tanlov ruxsat etilgan bo'lsa — uni qaytaradi", () => {
    expect(resolveInitialRegion(regions, 14)).toEqual(regions[1]);
  });

  it("saqlangan viloyat endi biriktirilmagan bo'lsa — qayta tanlash kerak", () => {
    expect(resolveInitialRegion(regions, 99)).toBeNull();
    expect(resolveInitialRegion(regions, null)).toBeNull();
  });
});

describe("errorMessage", () => {
  it("backend detail matnini ko'rsatadi", () => {
    expect(errorMessage(403, { detail: "Tanlangan region sizga biriktirilmagan" })).toBe(
      "Tanlangan region sizga biriktirilmagan",
    );
  });

  it("validatsiya xatosida birinchi aniq xatoni ko'rsatadi", () => {
    expect(
      errorMessage(422, { detail: "Validatsiya xatoligi", errors: ["body -> jshshir: String should match pattern"] }),
    ).toBe("body -> jshshir: String should match pattern");
  });

  it("javob bo'sh bo'lsa status bo'yicha tushunarli matn beradi", () => {
    expect(errorMessage(401, null)).toMatch(/qaytadan oching/);
    expect(errorMessage(502, "<html>")).toMatch(/Kutilmagan xatolik/);
  });
});
