import { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import apiClient from '@/api/client';

interface ContactOption {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
}

interface ContactSearchSelectProps {
  value: string | null;
  onChange: (contactId: string | null) => void;
  placeholder?: string;
  className?: string;
}

export const ContactSearchSelect = ({
  value,
  onChange,
  placeholder = 'Search contacts...',
  className,
}: ContactSearchSelectProps) => {
  const [search, setSearch] = useState('');
  const [options, setOptions] = useState<ContactOption[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedLabel, setSelectedLabel] = useState('');
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    // Load selected contact name
    if (value && !selectedLabel) {
      apiClient.get(`/contacts/${value}`).then(res => {
        const c = res.data;
        const name = [c.first_name, c.last_name].filter(Boolean).join(' ') || c.email;
        setSelectedLabel(name);
      }).catch(() => {});
    }
  }, [value, selectedLabel]);

  useEffect(() => {
    if (!search || search.length < 2) {
      setOptions([]);
      return;
    }

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await apiClient.get('/contacts', {
          params: { search, page_size: 10 },
        });
        setOptions(res.data.results ?? res.data);
      } catch {
        setOptions([]);
      }
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (contact: ContactOption) => {
    onChange(contact.id);
    const name = [contact.first_name, contact.last_name].filter(Boolean).join(' ') || contact.email;
    setSelectedLabel(name);
    setSearch('');
    setIsOpen(false);
  };

  const handleClear = () => {
    onChange(null);
    setSelectedLabel('');
    setSearch('');
  };

  return (
    <div ref={wrapperRef} className={`relative ${className || ''}`}>
      {value && selectedLabel ? (
        <div className="flex items-center justify-between border rounded-md px-3 py-2 text-sm">
          <span>{selectedLabel}</span>
          <button
            type="button"
            onClick={handleClear}
            className="text-muted-foreground hover:text-foreground ml-2"
          >
            &times;
          </button>
        </div>
      ) : (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            placeholder={placeholder}
            className="pl-9"
          />
        </div>
      )}

      {isOpen && options.length > 0 && (
        <div className="absolute z-50 w-full mt-1 bg-card border rounded-md shadow-lg max-h-60 overflow-auto">
          {options.map((contact) => {
            const name = [contact.first_name, contact.last_name].filter(Boolean).join(' ');
            return (
              <button
                key={contact.id}
                type="button"
                className="w-full text-left px-3 py-2 text-sm hover:bg-secondary transition-colors"
                onClick={() => handleSelect(contact)}
              >
                <div className="font-medium">{name || contact.email}</div>
                {name && (
                  <div className="text-xs text-muted-foreground">{contact.email}</div>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
