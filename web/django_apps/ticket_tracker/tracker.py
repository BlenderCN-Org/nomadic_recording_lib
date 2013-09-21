from django.db import models
from models_default_builder.models import build_defaults
    
class Tracker(models.Model):
    name = models.CharField(max_length=100)
    message_handler = models.ForeignKey('ticket_tracker.EmailHandler', 
                                        related_name='trackers', 
                                        blank=True, 
                                        null=True)
    hidden_data_delimiter = models.CharField(max_length=100, 
                                             default='_STAFF_ONLY_DATA_\n')
    def match_message(self, **kwargs):
        msg = kwargs.get('message')
        parsed_templates = kwargs.get('parsed_templates')
        q = self.tickets.all()
        for tname, tdata in parsed_templates.iteritems():
            for qstr, val in tdata['subject'].iteritems():
                if 'ticket' in qstr:
                    q = q.filter(**{qstr:val})
        count = q.count()
        if count == 1:
            ticket = q[0]
            return ticket.add_message(**kwargs)
        return False
    
class TrackerPermissionItem(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    inherited = models.ManyToManyField('self', blank=True, null=True)
    @classmethod
    def default_builder_create(cls, **kwargs):
        ckwargs = kwargs.copy()
        inherited = ckwargs.get('inherited')
        if inherited is not None:
            del ckwargs['inherited']
        obj = cls(**ckwargs)
        obj.save()
        if inherited is not None:
            for other in inherited:
                other_obj = cls.objects.get(name=other)
                obj.inherited.add(other_obj)
            obj.save()
    def default_builder_update(self, **kwargs):
        for fname, fval in kwargs.iteritems():
            if fname == 'inherited':
                for othername in fval:
                    self.inherited.add(TrackerPermissionItem.get(name=othername))
            else:
                setattr(self, fname, fval)
    def __unicode__(self):
        desc = self.description
        if desc:
            return desc
        return self.name
    
tracker_item_defaults = ({'name':'read', 'description':'Can Read Posts'}, 
                         {'name':'write', 'description':'Can Reply', 'inherited':['read']}, 
                         {'name':'modify', 'description':'Can Modify Posts', 'inherited':['write']}, 
                         {'name':'take', 'description':'Can Take Ticket as Assignment', 'inherited':['write']}, 
                         {'name':'assign', 'description':'Can Assign Tickets to Staff', 'inherited':['take']}, 
                         {'name':'status_change', 'description':'Can Change Ticket Status', 'inherited':['write']}, 
                         {'name':'all', 'description':'All Permissions (SuperUser)', 'inherited':['read', 
                                                                                                  'write', 
                                                                                                  'modify', 
                                                                                                  'take', 
                                                                                                  'assign', 
                                                                                                  'status_change']})

build_defaults({'model':TrackerPermissionItem, 'unique':'name', 'defaults':tracker_item_defaults})
    

    
class TrackerGlobalPermission(models.Model):
    permission = models.ForeignKey(TrackerPermissionItem)
    users = models.ManyToManyField('ticket_tracker.StaffUser', null=True, blank=True)
    groups = models.ManyToManyField('ticket_tracker.StaffGroup', null=True, blank=True)
    def __unicode__(self):
        return unicode(self.permission)
        
class TrackerPermission(models.Model):
    permission = models.ForeignKey(TrackerPermissionItem)
    users = models.ManyToManyField('ticket_tracker.StaffUser', null=True, blank=True)
    groups = models.ManyToManyField('ticket_tracker.StaffGroup', null=True, blank=True)
    tracker = models.ForeignKey(Tracker)
    def __unicode__(self):
        return unicode(self.permission)
