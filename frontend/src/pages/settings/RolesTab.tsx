import { useMemo, useState } from 'react';
import { Lock, Plus, Shield, Trash2, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  useCreateRole,
  useDeleteRole,
  usePermissionCatalog,
  useRoles,
  useUpdateRole,
} from '@/hooks/useTeam';
import { usePermissions } from '@/hooks/usePermissions';
import type { PermissionCatalog, Role } from '@/types/team';

/** Mirrors CUSTOM_ROLE_MIN_PLAN on the server. */
const CUSTOM_ROLE_MIN_PLAN = 'business';

function groupResources(catalog: PermissionCatalog | undefined) {
  const groups = new Map<string, PermissionCatalog['resources']>();
  for (const resource of catalog?.resources ?? []) {
    const existing = groups.get(resource.group) ?? [];
    existing.push(resource);
    groups.set(resource.group, existing);
  }
  return [...groups.entries()];
}

interface MatrixProps {
  catalog: PermissionCatalog | undefined;
  selected: Set<string>;
  onToggle?: (code: string) => void;
  readOnly?: boolean;
}

/**
 * The permission matrix: one row per resource, one checkbox per verb.
 *
 * Both the rows and the verbs come from the API, so a resource added on the
 * server shows up here without a frontend change — and a resource that is not
 * declared there cannot be granted here.
 */
function PermissionMatrix({ catalog, selected, onToggle, readOnly }: MatrixProps) {
  return (
    <div className="space-y-5">
      {groupResources(catalog).map(([group, resources]) => (
        <div key={group}>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {group}
          </p>
          <div className="space-y-2">
            {resources.map((resource) => (
              <div
                key={resource.key}
                className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-start sm:gap-4"
              >
                <div className="sm:w-48 sm:shrink-0">
                  <p className="text-sm font-medium">{resource.label}</p>
                </div>
                <div className="flex flex-wrap gap-x-5 gap-y-2">
                  {resource.verbs.map((verb) => (
                    <label
                      key={verb.code}
                      className={`flex items-center gap-2 text-sm ${
                        readOnly ? 'text-muted-foreground' : 'cursor-pointer'
                      }`}
                    >
                      <Checkbox
                        checked={selected.has(verb.code)}
                        disabled={readOnly}
                        onCheckedChange={() => onToggle?.(verb.code)}
                      />
                      {verb.label}
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

interface RoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: Role | null;
  catalog: PermissionCatalog | undefined;
  grantable: Set<string>;
}

function RoleDialog({ open, onOpenChange, role, catalog, grantable }: RoleDialogProps) {
  const [name, setName] = useState(role?.name ?? '');
  const [selected, setSelected] = useState<Set<string>>(
    new Set(role?.permissions ?? [])
  );
  const createRole = useCreateRole();
  const updateRole = useUpdateRole();
  const saving = createRole.isPending || updateRole.isPending;

  const toggle = (code: string) => {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data = { name, permissions: [...selected] };
    const done = { onSuccess: () => onOpenChange(false) };
    if (role) {
      updateRole.mutate({ roleId: role.id, data }, done);
    } else {
      createRole.mutate(data, done);
    }
  };

  // Only what this admin holds themselves: the API refuses the rest, and
  // offering a checkbox that cannot be saved is worse than not offering it.
  const offered = useMemo(() => {
    if (!catalog) return catalog;
    return {
      ...catalog,
      resources: catalog.resources
        .map((resource) => ({
          ...resource,
          verbs: resource.verbs.filter((verb) => grantable.has(verb.code)),
        }))
        .filter((resource) => resource.verbs.length > 0),
    };
  }, [catalog, grantable]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-[720px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{role ? 'Edit role' : 'New role'}</DialogTitle>
            <DialogDescription>
              {role
                ? 'Members keep this role while you change what it can do.'
                : 'Pick a name and tick what this role is allowed to do.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-5 py-4">
            <div className="grid gap-2">
              <Label htmlFor="role-name">Name</Label>
              <Input
                id="role-name"
                value={name}
                placeholder="Campaign Editor"
                onChange={(e) => setName(e.target.value)}
                required
              />
              {role && (
                <p className="text-xs text-muted-foreground">
                  Renaming is safe: members are linked by the role's id
                  (<code>{role.slug}</code>), not its name.
                </p>
              )}
            </div>

            <div>
              <Label>Permissions</Label>
              <p className="mb-3 mt-1 text-xs text-muted-foreground">
                {selected.size} selected
              </p>
              <PermissionMatrix
                catalog={offered}
                selected={selected}
                onToggle={toggle}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving || !name.trim()}>
              {saving ? 'Saving...' : role ? 'Save role' : 'Create role'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function RolesTab() {
  const { data: catalog, isLoading: loadingCatalog } = usePermissionCatalog();
  const { data: roles, isLoading: loadingRoles } = useRoles();
  const deleteRole = useDeleteRole();
  const { can, planAtLeast } = usePermissions();

  const [editing, setEditing] = useState<Role | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const canUseCustomRoles = planAtLeast(CUSTOM_ROLE_MIN_PLAN);
  const grantable = useMemo(() => {
    const codes = new Set<string>();
    for (const resource of catalog?.resources ?? []) {
      for (const verb of resource.verbs) {
        if (can(verb.code)) codes.add(verb.code);
      }
    }
    return codes;
  }, [catalog, can]);

  const openNew = () => {
    setEditing(null);
    setDialogOpen(true);
  };

  const openEdit = (role: Role) => {
    setEditing(role);
    setDialogOpen(true);
  };

  const previewed = catalog?.presets.find((preset) => preset.slug === preview);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Roles
            </CardTitle>
            <CardDescription>
              Every member has one role, and the role decides what they can
              reach. The four built-in roles cover most teams; add your own when
              they do not.
            </CardDescription>
          </div>
          {canUseCustomRoles && (
            <Button onClick={openNew} disabled={loadingCatalog}>
              <Plus className="mr-2 h-4 w-4" />
              New role
            </Button>
          )}
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <p className="mb-2 text-sm font-medium">Built-in</p>
            <div className="space-y-2">
              {(catalog?.presets ?? []).map((preset) => (
                <button
                  type="button"
                  key={preset.slug}
                  onClick={() =>
                    setPreview(preview === preset.slug ? null : preset.slug)
                  }
                  className="flex w-full items-center justify-between rounded-md border p-3 text-left hover:bg-accent"
                >
                  <span className="flex items-center gap-2 text-sm font-medium">
                    <Lock className="h-3.5 w-3.5 text-muted-foreground" />
                    {preset.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {preset.permissions.length} permissions
                    {preset.assignable ? '' : ' · by ownership transfer only'}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-2 text-sm font-medium">Your roles</p>
            {loadingRoles ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : (roles ?? []).length === 0 ? (
              <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                {canUseCustomRoles
                  ? 'No roles of your own yet.'
                  : `Custom roles are part of the ${CUSTOM_ROLE_MIN_PLAN} plan and above. The four built-in roles are available on every plan.`}
              </p>
            ) : (
              <div className="space-y-2">
                {(roles ?? []).map((role) => (
                  <div
                    key={role.id}
                    className="flex items-center justify-between gap-3 rounded-md border p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{role.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {role.permissions.length} permission
                        {role.permissions.length === 1 ? '' : 's'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {role.member_count > 0 && (
                        <Badge variant="outline" className="gap-1">
                          <Users className="h-3 w-3" />
                          {role.member_count}
                        </Badge>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEdit(role)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        // A role with members cannot be deleted; the API says
                        // so too, this just saves the round trip.
                        disabled={role.member_count > 0 || deleteRole.isPending}
                        title={
                          role.member_count > 0
                            ? 'Move its members to another role first'
                            : 'Delete this role'
                        }
                        onClick={() => deleteRole.mutate(role.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {previewed && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              What {previewed.name} can do
            </CardTitle>
            <CardDescription>
              Built-in roles cannot be edited. Copy one into a role of your own
              to change it.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PermissionMatrix
              catalog={catalog}
              selected={new Set(previewed.permissions)}
              readOnly
            />
          </CardContent>
        </Card>
      )}

      {dialogOpen && (
        <RoleDialog
          // Remounts per role, so the form starts from that role's values.
          key={editing?.id ?? 'new'}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          role={editing}
          catalog={catalog}
          grantable={grantable}
        />
      )}
    </div>
  );
}
