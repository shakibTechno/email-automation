import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Company, CreateCompanyData } from '@/types/crm';

const INDUSTRIES = [
  { value: 'technology', label: 'Technology' },
  { value: 'financial_services', label: 'Financial Services' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'retail', label: 'Retail' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'education', label: 'Education' },
  { value: 'media', label: 'Media & Entertainment' },
  { value: 'consulting', label: 'Consulting' },
  { value: 'other', label: 'Other' },
];

const SIZES = [
  { value: '1-10', label: '1–10 employees' },
  { value: '11-50', label: '11–50 employees' },
  { value: '51-200', label: '51–200 employees' },
  { value: '201-500', label: '201–500 employees' },
  { value: '501-1000', label: '501–1 000 employees' },
  { value: '1001+', label: '1 001+ employees' },
];

const schema = z.object({
  name: z.string().min(1, 'Company name is required').max(255),
  website: z.string().url('Must be a valid URL').or(z.literal('')).optional(),
  domain: z.string().max(255).optional(),
  industry: z.string().optional(),
  size: z.string().optional(),
  annual_revenue: z.coerce.number().positive().nullable().optional(),
  phone: z.string().max(30).optional(),
  address: z.string().optional(),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (data: CreateCompanyData) => Promise<void>;
  initialValues?: Partial<Company>;
  isSubmitting?: boolean;
}

export const CompanyFormDialog = ({
  open,
  onClose,
  onSubmit,
  initialValues,
  isSubmitting,
}: Props) => {
  const isEdit = !!initialValues?.id;

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      website: '',
      domain: '',
      industry: '',
      size: '',
      annual_revenue: null,
      phone: '',
      address: '',
      description: '',
    },
  });

  useEffect(() => {
    if (initialValues) {
      reset({
        name: initialValues.name ?? '',
        website: initialValues.website ?? '',
        domain: initialValues.domain ?? '',
        industry: initialValues.industry ?? '',
        size: initialValues.size ?? '',
        annual_revenue: initialValues.annual_revenue ?? null,
        phone: initialValues.phone ?? '',
        address: initialValues.address ?? '',
        description: initialValues.description ?? '',
      });
    } else {
      reset({
        name: '',
        website: '',
        domain: '',
        industry: '',
        size: '',
        annual_revenue: null,
        phone: '',
        address: '',
        description: '',
      });
    }
  }, [initialValues, reset]);

  const handleFormSubmit = handleSubmit(async (values) => {
    const payload: CreateCompanyData = {
      name: values.name,
      website: values.website || undefined,
      domain: values.domain || undefined,
      industry: (values.industry as any) || undefined,
      size: (values.size as any) || undefined,
      annual_revenue: values.annual_revenue ?? null,
      phone: values.phone || undefined,
      address: values.address || undefined,
      description: values.description || undefined,
    };
    await onSubmit(payload);
  });

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Company' : 'New Company'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleFormSubmit} className="space-y-4">
          <div>
            <Label htmlFor="name">Company Name *</Label>
            <Input id="name" {...register('name')} placeholder="Acme Corp" />
            {errors.name && (
              <p className="text-xs text-destructive mt-1">{errors.name.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="website">Website</Label>
              <Input id="website" {...register('website')} placeholder="https://example.com" />
              {errors.website && (
                <p className="text-xs text-destructive mt-1">{errors.website.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="domain">Domain</Label>
              <Input id="domain" {...register('domain')} placeholder="example.com" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Industry</Label>
              <Select value={watch('industry') || ''} onValueChange={(v) => setValue('industry', v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select industry" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {INDUSTRIES.map((i) => (
                    <SelectItem key={i.value} value={i.value}>{i.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Company Size</Label>
              <Select value={watch('size') || ''} onValueChange={(v) => setValue('size', v)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select size" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {SIZES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="phone">Phone</Label>
              <Input id="phone" {...register('phone')} placeholder="+1 555 000 0000" />
            </div>
            <div>
              <Label htmlFor="annual_revenue">Annual Revenue (USD)</Label>
              <Input
                id="annual_revenue"
                type="number"
                {...register('annual_revenue', { valueAsNumber: true })}
                placeholder="0"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="address">Address</Label>
            <Input id="address" {...register('address')} placeholder="123 Main St, City" />
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Brief description of the company..."
              rows={3}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving…' : isEdit ? 'Update Company' : 'Create Company'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
