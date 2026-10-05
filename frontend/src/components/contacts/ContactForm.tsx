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
import { TagSelector } from './TagSelector';
import { useTeamMembers } from '@/hooks/useTeam';

const contactSchema = z.object({
  email: z.string().email('Invalid email address'),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  phone: z.string().optional(),
  company: z.string().optional(),
  job_title: z.string().optional(),
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
          is_subscribed: contact.is_subscribed,
          assigned_to: contact.assigned_to ?? null,
          tags: tags.map((tag) => tag.id),
        }
      : {
          is_subscribed: true,
          assigned_to: null,
          tags: [],
        },
  });

  const isSubscribed = watch('is_subscribed');
  const tagIds = watch('tags') || [];
  const assignedTo = watch('assigned_to');

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
