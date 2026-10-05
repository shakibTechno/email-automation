import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ContactForm } from '@/components/contacts/ContactForm';
import { useContact, useContacts } from '@/hooks/useContacts';
import { UpdateContactData } from '@/types/contact';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useState } from 'react';

export const ContactEditPage = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const contactId = id || '';
  const { contact, isLoading } = useContact(contactId);
  const { updateContact, deleteContact, isUpdating } = useContacts();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleSubmit = (data: UpdateContactData) => {
    updateContact(contactId, data);
    navigate(`/contacts/${contactId}`);
  };

  const handleDelete = () => {
    deleteContact(contactId);
    navigate('/contacts');
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="w-full">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Contact not found</h2>
          <Button onClick={() => navigate('/contacts')} className="mt-4">
            Back to Contacts
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/contacts')}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold">Edit Contact</h1>
            <p className="text-muted-foreground">
              Update contact information
            </p>
          </div>
        </div>
        <Button
          variant="destructive"
          onClick={() => setDeleteDialogOpen(true)}
        >
          <Trash2 className="h-4 w-4 mr-2" />
          Delete
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Contact Information</CardTitle>
        </CardHeader>
        <CardContent>
          <ContactForm
            contact={contact}
            onSubmit={handleSubmit}
            isSubmitting={isUpdating}
          />
        </CardContent>
      </Card>

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Contact</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this contact? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
