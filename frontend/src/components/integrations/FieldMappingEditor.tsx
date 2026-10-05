import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { FieldMappingOption } from '@/types/integration';

interface FieldMappingEditorProps {
  mapping: Record<string, string>;
  onChange: (mapping: Record<string, string>) => void;
  options: FieldMappingOption[];
}

const SOURCE_FIELDS = [
  { key: 'email', label: 'Email' },
  { key: 'first_name', label: 'First Name' },
  { key: 'last_name', label: 'Last Name' },
  { key: 'phone', label: 'Phone' },
  { key: 'company', label: 'Company' },
  { key: 'job_title', label: 'Job Title' },
];

const DO_NOT_MAP_VALUE = '__none__';

export function FieldMappingEditor({ mapping, onChange, options }: FieldMappingEditorProps) {
  const handleFieldChange = (sourceKey: string, targetValue: string) => {
    const newMapping = { ...mapping };
    if (targetValue === DO_NOT_MAP_VALUE) {
      delete newMapping[sourceKey];
    } else {
      newMapping[sourceKey] = targetValue;
    }
    onChange(newMapping);
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Platform Source Field</TableHead>
          <TableHead>Contact Field</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {SOURCE_FIELDS.map((field) => (
          <TableRow key={field.key}>
            <TableCell className="font-medium">{field.label}</TableCell>
            <TableCell>
              <Select
                value={mapping[field.key] || DO_NOT_MAP_VALUE}
                onValueChange={(value) => handleFieldChange(field.key, value)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select field" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={DO_NOT_MAP_VALUE}>-- Do not map --</SelectItem>
                  {options.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
