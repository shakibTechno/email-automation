import {
  BellRing, Briefcase, Calendar, CheckCircle2, CheckSquare, Circle,
  CircleSlash, Clock, FileText, Gauge, GitBranch, GitFork,
  GitPullRequestArrow, Globe, Hourglass, ListChecks, ListX, Mail, MailOpen,
  MailWarning, MailX, Maximize2, MousePointerClick, PencilLine, Split, Square,
  StickyNote, Tag, Target, Trophy, UserCheck, UserCog, UserPlus,
  UserRoundMinus, UsersRound, Webhook, Workflow, XOctagon,
  type LucideIcon,
} from 'lucide-react';

/**
 * The icons the node catalogue names.
 *
 * Named explicitly rather than looked up on lucide's whole export. `import *
 * from 'lucide-react'` defeats tree-shaking and added 110 kB gzipped to every
 * page in the app — for icon lookup convenience on one panel.
 *
 * A node type whose icon is not here renders a plain circle, which is a
 * visible blemish rather than a crash. If you add a node type with a new
 * icon, add it here too; nothing breaks in the meantime.
 */
const ICONS: Record<string, LucideIcon> = {
  BellRing,
  Briefcase,
  Calendar,
  CheckCircle2,
  CheckSquare,
  CircleSlash,
  Clock,
  FileText,
  Gauge,
  GitBranch,
  GitFork,
  GitPullRequestArrow,
  Globe,
  Hourglass,
  ListChecks,
  ListX,
  Mail,
  MailOpen,
  MailWarning,
  MailX,
  Maximize2,
  MousePointerClick,
  PencilLine,
  Split,
  Square,
  StickyNote,
  Tag,
  // lucide ships neither TagPlus nor TagMinus. The catalogue asks for both,
  // and a tag icon is a better stand-in than a blank circle.
  TagPlus: Tag,
  TagMinus: Tag,
  Target,
  Trophy,
  UserCheck,
  UserCog,
  UserPlus,
  UserRoundMinus,
  UsersRound,
  Webhook,
  Workflow,
  XOctagon,
};

export function nodeIcon(name: string, className = 'h-4 w-4') {
  const Component = ICONS[name] ?? Circle;
  return <Component className={className} />;
}
