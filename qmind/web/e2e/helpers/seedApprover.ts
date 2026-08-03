import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";

/** Insert a second active membership (quality_manager) in Demo Org for SoD approvals. */
export function seedSecondApprover(orgId: string): {
  membershipId: string;
  sub: string;
  email: string;
} {
  const sub = `e2e-approver-${randomUUID()}`;
  const email = `${sub}@example.com`;
  const sql = `
    WITH u AS (
      INSERT INTO users (idp_sub, email, status)
      VALUES ('${sub}', '${email}', 'active')
      RETURNING id
    )
    INSERT INTO memberships (organization_id, user_id, roles, status)
    SELECT '${orgId}'::uuid, u.id, ARRAY['quality_manager']::text[], 'active'
    FROM u
    RETURNING id;
  `;
  const out = execFileSync(
    "docker",
    ["exec", "-i", "leaction_db", "psql", "-U", "admin", "-d", "qmind", "-t", "-A", "-c", sql],
    { encoding: "utf8" },
  );
  const membershipId = out
    .trim()
    .split(/\r?\n/)
    .map((l) => l.trim())
    .find((l) => /^[0-9a-f-]{36}$/i.test(l));
  if (!membershipId) {
    throw new Error(`seedSecondApprover failed: ${out}`);
  }
  return { membershipId, sub, email };
}
