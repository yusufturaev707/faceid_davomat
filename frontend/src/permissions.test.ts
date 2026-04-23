import { describe, it, expect } from "vitest";
import { PERM, P } from "./permissions";

describe("permissions catalog", () => {
  it("P va PERM bir xil obyekt", () => {
    expect(P).toBe(PERM);
  });

  it("barcha codename'lar <group>:<action> formatida", () => {
    for (const code of Object.values(PERM)) {
      expect(code).toMatch(/^[a-z_]+:[a-z_]+$/);
    }
  });

  it("takroriy codename yo'q", () => {
    const codes = Object.values(PERM);
    expect(new Set(codes).size).toBe(codes.length);
  });

  it("kritik permission'lar mavjud", () => {
    expect(PERM.USER_READ).toBe("user:read");
    expect(PERM.ROLE_UPDATE).toBe("role:update");
    expect(PERM.STUDENT_LOG_CREATE).toBe("student_log:create");
  });
});
