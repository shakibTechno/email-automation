import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ContactForm } from '@/components/contacts/ContactForm';
import { useContacts } from '@/hooks/useContacts';
import { CreateContactData } from '@/types/contact';

export const ContactCreatePage = () => {
  const navigate = useNavigate();
  const { createContact, isCreating } = useContacts();

  const handleSubmit = (data: CreateContactData) => {
    createContact(data);
    navigate('/contacts');
  };

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/contacts')}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Create Contact</h1>
          <p className="text-muted-foreground">
            Add a new contact to your email list
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Contact Information</CardTitle>
        </CardHeader>
        <CardContent>
          <ContactForm onSubmit={handleSubmit} isSubmitting={isCreating} />
        </CardContent>
      </Card>
    </div>
  );
};
