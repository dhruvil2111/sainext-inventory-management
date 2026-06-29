import { PageHeader } from "@/components/layout/PageHeader";
import { Card, EmptyState } from "@/components/ui";
import { Wrench } from "@phosphor-icons/react";

export default function ComingSoon({ title, phase }: { title: string; phase?: string }) {
  return (
    <div>
      <PageHeader title={title} subtitle={phase ? `Planned for ${phase}` : undefined} />
      <Card>
        <EmptyState icon={<Wrench size={22} weight="duotone" />} title={`${title} is coming soon`}
          hint="This module is part of a later delivery phase. The navigation, permissions, and data model are already in place - the screen will light up when its phase ships." />
      </Card>
    </div>
  );
}
