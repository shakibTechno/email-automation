import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  ArrowLeft,
  Edit,
  Play,
  Pause,
  Users,
  CheckCircle,
  TrendingUp,
  Mail,
  MoreHorizontal,
  XCircle,
} from 'lucide-react';
import { useSequence, useSequenceStats, useSequenceEnrollments, useSequenceMutations } from '@/hooks/useSequences';
import { format } from 'date-fns';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-success/[.14] text-success',
  completed: 'bg-info/[.14] text-info',
  cancelled: 'bg-secondary text-muted-foreground',
  unsubscribed: 'bg-destructive/[.14] text-destructive',
  paused: 'bg-warning/[.14] text-warning',
};

export default function SequenceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [enrollmentStatus, setEnrollmentStatus] = useState('');

  const { data: sequence, isLoading } = useSequence(id!);
  const { data: stats } = useSequenceStats(id!);
  const { data: enrollments = [] } = useSequenceEnrollments(id!, enrollmentStatus ? { status: enrollmentStatus } : {});
  const { activate, pause } = useSequenceMutations();

  if (isLoading || !sequence) {
    return <div className="p-6 text-muted-foreground">Loading...</div>;
  }

  const seqStatus = sequence.status;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/sequences')}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{sequence.name}</h1>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[seqStatus] || 'bg-secondary text-muted-foreground'}`}>
                {seqStatus.charAt(0).toUpperCase() + seqStatus.slice(1)}
              </span>
            </div>
            {sequence.description && (
              <p className="text-sm text-muted-foreground mt-1">{sequence.description}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          {seqStatus === 'active' ? (
            <Button variant="outline" onClick={() => pause.mutate(id!)}>
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </Button>
          ) : (seqStatus === 'draft' || seqStatus === 'paused') ? (
            <Button onClick={() => activate.mutate(id!)} className="bg-success hover:bg-success/90">
              <Play className="h-4 w-4 mr-2" />
              Activate
            </Button>
          ) : null}
          <Button variant="outline" onClick={() => navigate(`/sequences/${id}/edit`)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                <Users className="h-4 w-4" />
                Active Enrolled
              </div>
              <p className="text-2xl font-bold">{stats.active}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                <CheckCircle className="h-4 w-4" />
                Completed
              </div>
              <p className="text-2xl font-bold">{stats.completed}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                <TrendingUp className="h-4 w-4" />
                Completion Rate
              </div>
              <p className="text-2xl font-bold">{stats.completion_rate}%</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                <Mail className="h-4 w-4" />
                Total Steps
              </div>
              <p className="text-2xl font-bold">{sequence.steps.length}</p>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Steps Panel */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-lg font-semibold">Sequence Steps</h2>
          {sequence.steps.length === 0 ? (
            <Card>
              <CardContent className="py-8 text-center text-subtle-foreground text-sm">
                No steps configured yet.
                <br />
                <Button size="sm" variant="link" onClick={() => navigate(`/sequences/${id}/edit`)}>
                  Add steps
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {sequence.steps.map((step, idx) => {
                const stepStat = stats?.steps?.find((s) => s.position === step.position);
                return (
                  <Card key={step.id} className="border">
                    <CardContent className="py-3 px-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-subtle-foreground font-semibold uppercase">Step {idx + 1}</span>
                        {(step.delay_days > 0 || step.delay_hours > 0) && (
                          <span className="text-xs text-brand">
                            +{step.delay_days > 0 ? `${step.delay_days}d ` : ''}{step.delay_hours > 0 ? `${step.delay_hours}h` : ''}
                          </span>
                        )}
                      </div>
                      <p className="text-sm font-medium truncate">{step.subject}</p>
                      {stepStat && stepStat.sent > 0 && (
                        <div className="flex gap-3 mt-2 text-xs text-muted-foreground">
                          <span>{stepStat.sent} sent</span>
                          <span>{stepStat.open_rate}% opened</span>
                          <span>{stepStat.click_rate}% clicked</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* Enrollments Panel */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Enrolled Contacts</h2>
            <select
              value={enrollmentStatus}
              onChange={(e) => setEnrollmentStatus(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
              <option value="unsubscribed">Unsubscribed</option>
              <option value="paused">Paused</option>
            </select>
          </div>

          {enrollments.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center text-subtle-foreground text-sm">
                No contacts enrolled{enrollmentStatus ? ` with status "${enrollmentStatus}"` : ''} yet.
              </CardContent>
            </Card>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Contact</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Step</TableHead>
                    <TableHead>Next Send</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {enrollments.map((enrollment) => (
                    <TableRow key={enrollment.id}>
                      <TableCell>
                        <div className="font-medium text-sm">{enrollment.contact_name}</div>
                        <div className="text-xs text-muted-foreground">{enrollment.contact_email}</div>
                      </TableCell>
                      <TableCell>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[enrollment.status] || ''}`}>
                          {enrollment.status.charAt(0).toUpperCase() + enrollment.status.slice(1)}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {enrollment.status === 'completed'
                          ? 'Done'
                          : `Step ${enrollment.current_step_position + 1}`}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {enrollment.next_send_at
                          ? format(new Date(enrollment.next_send_at), 'MMM d, h:mm a')
                          : '—'}
                      </TableCell>
                      <TableCell>
                        {enrollment.status === 'active' && (
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-7 w-7">
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={async () => {
                                  const { sequencesApi } = await import('@/api/sequences');
                                  await sequencesApi.cancelEnrollment(enrollment.id);
                                }}
                              >
                                <XCircle className="h-4 w-4 mr-2" />
                                Cancel Enrollment
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
