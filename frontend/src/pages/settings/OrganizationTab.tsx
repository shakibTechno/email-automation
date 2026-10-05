import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useOrganizationSettings, useUpdateOrganization } from '@/hooks/useTeam';
import { usePermissions } from '@/hooks/usePermissions';
import type { UpdateOrganizationData } from '@/types/team';

export function OrganizationTab() {
  const { data: org, isLoading } = useOrganizationSettings();
  const updateOrg = useUpdateOrganization();
  const { isAdmin } = usePermissions();

  const { register, handleSubmit, reset } = useForm<UpdateOrganizationData>();

  useEffect(() => {
    if (org) {
      reset({
        name: org.name,
        domain: org.domain,
        email: org.email,
        phone: org.phone,
        address_line1: org.address_line1,
        address_line2: org.address_line2,
        city: org.city,
        state: org.state,
        country: org.country,
        postal_code: org.postal_code,
      });
    }
  }, [org, reset]);

  const onSubmit = (data: UpdateOrganizationData) => {
    updateOrg.mutate(data);
  };

  if (isLoading) {
    return <div className="text-center py-8 text-muted-foreground">Loading organization settings...</div>;
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>General Information</CardTitle>
          <CardDescription>Basic information about your organization.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Organization Name</Label>
              <Input id="name" {...register('name')} disabled={!isAdmin} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="domain">Domain</Label>
              <Input id="domain" {...register('domain')} placeholder="example.com" disabled={!isAdmin} />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...register('email')} disabled={!isAdmin} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input id="phone" {...register('phone')} disabled={!isAdmin} />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Address</CardTitle>
          <CardDescription>Organization's physical address.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="address_line1">Address Line 1</Label>
            <Input id="address_line1" {...register('address_line1')} disabled={!isAdmin} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="address_line2">Address Line 2</Label>
            <Input id="address_line2" {...register('address_line2')} disabled={!isAdmin} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="city">City</Label>
              <Input id="city" {...register('city')} disabled={!isAdmin} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="state">State</Label>
              <Input id="state" {...register('state')} disabled={!isAdmin} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="postal_code">Postal Code</Label>
              <Input id="postal_code" {...register('postal_code')} disabled={!isAdmin} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="country">Country</Label>
            <Input id="country" {...register('country')} disabled={!isAdmin} />
          </div>
        </CardContent>
      </Card>

      {org && (
        <Card>
          <CardHeader>
            <CardTitle>Plan & Limits</CardTitle>
            <CardDescription>Your current plan details (read-only).</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label className="text-muted-foreground">Plan</Label>
                <p className="font-medium capitalize">{org.plan}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Max Contacts</Label>
                <p className="font-medium">{org.max_contacts.toLocaleString()}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Max Emails / Month</Label>
                <p className="font-medium">{org.max_emails_per_month.toLocaleString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {isAdmin && (
        <div className="flex justify-end">
          <Button type="submit" disabled={updateOrg.isPending}>
            {updateOrg.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      )}
    </form>
  );
}
