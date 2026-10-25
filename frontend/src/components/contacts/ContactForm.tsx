import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Contact } from '@/types/contact';
import { formatDateTime } from '@/lib/utils';
import { TagSelector } from './TagSelector';
import { ContactSection } from './ContactSection';
import { useTeamMembers } from '@/hooks/useTeam';

const LIFECYCLE_STAGES = [
  { value: 'subscriber', label: 'Subscriber' },
  { value: 'lead', label: 'Lead' },
  { value: 'qualified', label: 'Qualified Lead' },
  { value: 'customer', label: 'Customer' },
  { value: 'evangelist', label: 'Evangelist' },
];

// Optional and trimmed to undefined when blank: the API treats an absent
// field as "leave it alone" and an empty string as "clear it", and sending
// the latter for every untouched input would wipe fields nobody edited.
const optionalText = z.string().trim().optional();

const contactSchema = z.object({
  email: z.string().email('Invalid email address'),
  first_name: optionalText,
  last_name: optionalText,
  phone: optionalText,
  company: optionalText,
  job_title: optionalText,

  // Personal
  salutation: optionalText,
  middle_name: optionalText,
  preferred_name: optionalText,
  mobile_phone: optionalText,
  date_of_birth: optionalText,
  website: z.string().trim().url('Enter a full URL, e.g. https://example.com').or(z.literal('')).optional(),
  linkedin_url: z.string().trim().url('Enter a full URL').or(z.literal('')).optional(),

  // Address
  address_line1: optionalText,
  address_line2: optionalText,
  city: optionalText,
  region: optionalText,
  postal_code: optionalText,
  country: z.string().trim().length(2, 'Use the two-letter country code, e.g. GB').or(z.literal('')).optional(),

  // Locale and lifecycle
  timezone: optionalText,
  locale: optionalText,
  lifecycle_stage: z.string().optional(),

  // Consent
  consent_source: optionalText,
  external_id: optionalText,

  is_subscribed: z.boolean().optional(),
  assigned_to: z.string().nullable().optional(),
  tags: z.array(z.string()).optional(),
});

type ContactFormData = z.infer<typeof contactSchema>;

interface ContactFormProps {
  contact?: Contact;
  onSubmit: (data: any) => void;
  isSubmitting?: boolean;
}

/**
 * One labelled input.
 *
 * The form grew from eight fields to about thirty; writing each one out
 * longhand would be six hundred lines of near-identical markup, and the ones
 * that differ would stop being visible.
 */
const Field = ({
  id,
  label,
  hint,
  error,
  ...props
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
} & React.ComponentProps<typeof Input>) => (
  <div className="space-y-2">
    <Label htmlFor={id}>{label}</Label>
    <Input id={id} {...props} />
    {hint && <p className="text-[11.5px] text-muted-foreground">{hint}</p>}
    {error && <p className="text-sm text-destructive">{error}</p>}
  </div>
);

export const ContactForm = ({ contact, onSubmit, isSubmitting }: ContactFormProps) => {
  const tags = contact?.tag_details || contact?.tags || [];
  const { data: members = [] } = useTeamMembers();
  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<ContactFormData>({
    resolver: zodResolver(contactSchema),
    defaultValues: contact
      ? {
          email: contact.email,
          first_name: contact.first_name || '',
          last_name: contact.last_name || '',
          phone: contact.phone || '',
          company: contact.company || '',
          job_title: contact.job_title || '',
          salutation: contact.salutation || '',
          middle_name: contact.middle_name || '',
          preferred_name: contact.preferred_name || '',
          mobile_phone: contact.mobile_phone || '',
          date_of_birth: contact.date_of_birth || '',
          website: contact.website || '',
          linkedin_url: contact.linkedin_url || '',
          address_line1: contact.address_line1 || '',
          address_line2: contact.address_line2 || '',
          city: contact.city || '',
          region: contact.region || '',
          postal_code: contact.postal_code || '',
          country: contact.country || '',
          timezone: contact.timezone || '',
          locale: contact.locale || '',
          lifecycle_stage: contact.lifecycle_stage || 'subscriber',
          consent_source: contact.consent_source || '',
          external_id: contact.external_id || '',
          is_subscribed: contact.is_subscribed,
          assigned_to: contact.assigned_to ?? null,
          tags: tags.map((tag) => tag.id),
        }
      : {
          is_subscribed: true,
          lifecycle_stage: 'subscriber',
          assigned_to: null,
          tags: [],
        },
  });

  const isSubscribed = watch('is_subscribed');
  const tagIds = watch('tags') || [];
  const assignedTo = watch('assigned_to');
  const values = watch();

  /** Register an input and hand it its own error, so each call site is one line. */
  const bind = (name: keyof ContactFormData) => ({
    ...register(name),
    disabled: isSubmitting,
    error: (errors as Record<string, { message?: string } | undefined>)[name]?.message,
  });

  /**
   * How many of these fields hold a value.
   *
   * Shown on a collapsed section so a contact's data is never hidden without a
   * sign that it is there — collapsing by default is only acceptable if a full
   * section announces itself.
   */
  const filled = (names: string[]) =>
    names.filter((name) => {
      const value = (values as Record<string, unknown>)[name];
      return value !== undefined && value !== null && value !== '';
    }).length;

  const handleFormSubmit = (data: ContactFormData) => {
    onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="first_name">First Name</Label>
          <Input
            id="first_name"
            placeholder="John"
            {...register('first_name')}
            disabled={isSubmitting}
          />
          {errors.first_name && (
            <p className="text-sm text-destructive">{errors.first_name.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="last_name">Last Name</Label>
          <Input
            id="last_name"
            placeholder="Doe"
            {...register('last_name')}
            disabled={isSubmitting}
          />
          {errors.last_name && (
            <p className="text-sm text-destructive">{errors.last_name.message}</p>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="email">
          Email <span className="text-destructive">*</span>
        </Label>
        <Input
          id="email"
          type="email"
          placeholder="john.doe@example.com"
          {...register('email')}
          disabled={isSubmitting}
        />
        {errors.email && (
          <p className="text-sm text-destructive">{errors.email.message}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="phone">Phone</Label>
          <Input
            id="phone"
            type="tel"
            placeholder="+1 (555) 123-4567"
            {...register('phone')}
            disabled={isSubmitting}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="company">Company</Label>
          <Input
            id="company"
            placeholder="Acme Inc."
            {...register('company')}
            disabled={isSubmitting}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="job_title">Job Title</Label>
        <Input
          id="job_title"
          placeholder="Marketing Manager"
          {...register('job_title')}
          disabled={isSubmitting}
        />
      </div>

      <ContactSection
        title="Personal details"
        description="Name, birthday, links"
        filledCount={filled([
          'salutation', 'middle_name', 'preferred_name', 'mobile_phone',
          'date_of_birth', 'website', 'linkedin_url',
        ])}
      >
        <div className="grid grid-cols-3 gap-4">
          <Field id="salutation" label="Salutation" placeholder="Dr" {...bind('salutation')} />
          <Field id="middle_name" label="Middle Name" {...bind('middle_name')} />
          <Field
            id="preferred_name"
            label="Preferred Name"
            placeholder="Jo"
            {...bind('preferred_name')}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field id="mobile_phone" label="Mobile Phone" type="tel" {...bind('mobile_phone')} />
          {/* The Birthday workflow template reads this. It shipped before the
              field existed, so the template could never fire. */}
          <Field id="date_of_birth" label="Date of Birth" type="date" {...bind('date_of_birth')} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <Field
            id="website"
            label="Website"
            placeholder="https://example.com"
            {...bind('website')}
          />
          <Field id="linkedin_url" label="LinkedIn" {...bind('linkedin_url')} />
        </div>
      </ContactSection>

      <ContactSection
        title="Address and locale"
        description="Geographic segments, send times, the email footer"
        filledCount={filled([
          'address_line1', 'address_line2', 'city', 'region', 'postal_code',
          'country', 'timezone', 'locale',
        ])}
      >
        <Field id="address_line1" label="Address Line 1" {...bind('address_line1')} />
        <Field id="address_line2" label="Address Line 2" {...bind('address_line2')} />
        <div className="grid grid-cols-3 gap-4">
          <Field id="city" label="City" {...bind('city')} />
          <Field id="region" label="State / Region" {...bind('region')} />
          <Field id="postal_code" label="Postal Code" {...bind('postal_code')} />
        </div>
        <div className="grid grid-cols-3 gap-4">
          <Field id="country" label="Country" placeholder="GB" {...bind('country')} />
          {/* Without these every send goes out on the sender's clock, which is
              3am for a good share of any international list. */}
          <Field
            id="timezone"
            label="Time Zone"
            placeholder="Europe/London"
            {...bind('timezone')}
          />
          <Field id="locale" label="Language" placeholder="en-GB" {...bind('locale')} />
        </div>
      </ContactSection>

      <ContactSection
        title="Consent and source"
        description="What you can show if consent is challenged"
        filledCount={filled(['consent_source', 'external_id'])}
      >
        <Field
          id="consent_source"
          label="Consent Source"
          placeholder="Newsletter form, 12 January 2026"
          hint="Where and how this contact agreed to be emailed."
          {...bind('consent_source')}
        />
        <Field
          id="external_id"
          label="External ID"
          hint="This contact's identifier in another system, so repeated syncs update rather than duplicate."
          {...bind('external_id')}
        />
        {contact && (
          <div className="grid grid-cols-2 gap-4 text-[12.5px]">
            <div>
              <p className="stat-label">Consent recorded</p>
              <p>{contact.consent_at ? formatDateTime(contact.consent_at) : '—'}</p>
            </div>
            <div>
              <p className="stat-label">Double opt-in</p>
              <p>{contact.double_opt_in_at ? formatDateTime(contact.double_opt_in_at) : '—'}</p>
            </div>
          </div>
        )}
      </ContactSection>

      <div className="space-y-2">
        <Label>Lifecycle Stage</Label>
        <Select
          value={watch('lifecycle_stage') || 'subscriber'}
          onValueChange={(v) => setValue('lifecycle_stage', v)}
          disabled={isSubmitting}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LIFECYCLE_STAGES.map((stage) => (
              <SelectItem key={stage.value} value={stage.value}>
                {stage.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Read-only on purpose: the server derives it from the subscription
          flags, so there is one definition of the contact's state rather than
          an editable copy that can disagree with it. */}
      {contact?.status && (
        <div className="flex flex-wrap items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-[12.5px]">
          <span className="stat-label">Status</span>
          <span className="font-medium capitalize">{contact.status}</span>
          {contact.bounce_type && (
            <span className="text-muted-foreground">({contact.bounce_type} bounce)</span>
          )}
          <span className="ml-auto text-[11.5px] text-muted-foreground">
            Follows the subscription setting below
          </span>
        </div>
      )}

      <div className="flex items-center space-x-2">
        <Checkbox
          id="is_subscribed"
          checked={isSubscribed}
          onCheckedChange={(checked) => setValue('is_subscribed', checked as boolean)}
          disabled={isSubmitting}
        />
        <Label htmlFor="is_subscribed" className="cursor-pointer">
          Subscribed to emails
        </Label>
      </div>

      <div className="space-y-2">
        <Label>Assigned To</Label>
        <Select
          value={assignedTo ?? 'unassigned'}
          onValueChange={(v) => setValue('assigned_to', v === 'unassigned' ? null : v)}
          disabled={isSubmitting}
        >
          <SelectTrigger>
            <SelectValue placeholder="Unassigned" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="unassigned">Unassigned</SelectItem>
            {members.map((m: any) => (
              <SelectItem key={m.id} value={m.id}>
                {m.full_name || m.email}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Tags</Label>
        <TagSelector
          selectedTagIds={tagIds}
          onChange={(ids) => setValue('tags', ids)}
          disabled={isSubmitting}
        />
      </div>

      <div className="flex gap-4">
        <Button type="submit" disabled={isSubmitting} className="flex-1">
          {isSubmitting ? 'Saving...' : contact ? 'Update Contact' : 'Create Contact'}
        </Button>
      </div>
    </form>
  );
};
