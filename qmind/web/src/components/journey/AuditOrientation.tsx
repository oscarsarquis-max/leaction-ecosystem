import { PageHeader } from "@/components/qm/PageHeader";

type Props = {
  title: string;
  explanation: string;
  expectedResult: string;
  stepProgress?: string;
  nextAction?: string;
};

/** Compat: preferir `PageHeader` de `@/components/qm`. */
export function AuditOrientation({
  title,
  explanation,
  expectedResult,
  stepProgress,
  nextAction,
}: Props) {
  return (
    <PageHeader
      title={title}
      explanation={explanation}
      expectedResult={expectedResult}
      progress={stepProgress}
      nextStep={nextAction}
    />
  );
}
