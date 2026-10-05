import { useState } from 'react';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Plus, Pencil, Trash2 } from 'lucide-react';
import { useScoringRules, useDeleteScoringRule, useToggleScoringRule } from '@/hooks/useLeadScoring';
import { ScoringRuleForm } from './ScoringRuleForm';
import type { ScoringRule } from '@/types/leadScoring';

function PointsBadge({ points }: { points: number }) {
  const positive = points >= 0;
  return (
    <Badge
      variant="outline"
      className={positive ? 'text-green-700 border-green-300 bg-green-50' : 'text-red-700 border-red-300 bg-red-50'}
    >
      {positive ? '+' : ''}{points}
    </Badge>
  );
}

export function ScoringRuleList() {
  const { data, isLoading } = useScoringRules();
  const deleteRule = useDeleteScoringRule();
  const toggleRule = useToggleScoringRule();

  const [formOpen, setFormOpen] = useState(false);
  const [editRule, setEditRule] = useState<ScoringRule | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const rules = data?.results ?? [];

  function openEdit(rule: ScoringRule) {
    setEditRule(rule);
    setFormOpen(true);
  }

  function closeForm() {
    setFormOpen(false);
    setEditRule(null);
  }

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">Scoring Rules</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Define demographic and behavioral rules that award or deduct points.
            </p>
          </div>
          <Button size="sm" onClick={() => { setEditRule(null); setFormOpen(true); }}>
            <Plus className="h-4 w-4 mr-1.5" />
            Add Rule
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">Loading rules…</div>
          ) : rules.length === 0 ? (
            <div className="py-12 text-center space-y-3">
              <p className="text-muted-foreground text-sm">No scoring rules yet.</p>
              <Button size="sm" variant="outline" onClick={() => setFormOpen(true)}>
                Create your first rule
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Points</TableHead>
                  <TableHead>Trigger</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="w-20" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rules.map((rule) => (
                  <TableRow key={rule.id}>
                    <TableCell className="font-medium">{rule.name}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="capitalize">
                        {rule.rule_type}
                      </Badge>
                    </TableCell>
                    <TableCell><PointsBadge points={rule.points} /></TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {rule.rule_type === 'behavioral'
                        ? rule.event_type?.replace(/_/g, ' ')
                        : `${rule.condition?.field ?? ''} ${rule.condition?.operator ?? ''}`}
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={rule.is_active}
                        onCheckedChange={() => toggleRule.mutate(rule.id)}
                        disabled={toggleRule.isPending}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button size="icon" variant="ghost" onClick={() => openEdit(rule)}>
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setDeleteId(rule.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ScoringRuleForm open={formOpen} onClose={closeForm} editRule={editRule} />

      <AlertDialog open={!!deleteId} onOpenChange={(v) => { if (!v) setDeleteId(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete scoring rule?</AlertDialogTitle>
            <AlertDialogDescription>
              This rule will no longer award or deduct points. Existing score history is preserved.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (deleteId) deleteRule.mutate(deleteId, { onSuccess: () => setDeleteId(null) });
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
