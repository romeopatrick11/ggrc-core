# Copyright (C) 2013 Google Inc., authors, and contributors <see AUTHORS file>
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>
# Created By: dan@reciprocitylabs.com
# Maintained By: dan@reciprocitylabs.com

from flask import Blueprint
from ggrc import settings
#from ggrc.app import app
#from ggrc.rbac import permissions
from ggrc.services.registry import service
from ggrc.views.registry import object_view
import ggrc_workflows.models as models


# Initialize Flask Blueprint for extension
blueprint = Blueprint(
  'ggrc_workflows',
  __name__,
  template_folder='templates',
  static_folder='static',
  static_url_path='/static/ggrc_workflows',
)


from ggrc.models import all_models

_workflow_object_types = [
    "Program",
    "Regulation", "Standard", "Policy", "Contract",
    "Objective", "Control", "Section", "Clause",
    "System", "Process",
    "DataAsset", "Facility", "Market", "Product", "Project"
    ]

for type_ in _workflow_object_types:
  model = getattr(all_models, type_)
  model.__bases__ = (
    models.workflow_object.Workflowable,
    models.task_group_object.TaskGroupable,
    ) + model.__bases__
  model.late_init_workflowable()
  model.late_init_task_groupable()


def get_public_config(current_user):
  """Expose additional permissions-dependent config to client.
  """
  return {}
#  public_config = {}
#  if permissions.is_admin():
#    if hasattr(settings, 'RISK_ASSESSMENT_URL'):
#      public_config['RISK_ASSESSMENT_URL'] = settings.RISK_ASSESSMENT_URL
#  return public_config


# Initialize service endpoints

def contributed_services():
  return [
      service('workflows', models.Workflow),
      service('workflow_objects', models.WorkflowObject),
      service('workflow_people', models.WorkflowPerson),
      service('tasks', models.Task),
      service('workflow_tasks', models.WorkflowTask),
      service('task_groups', models.TaskGroup),
      service('task_group_tasks', models.TaskGroupTask),
      service('task_group_objects', models.TaskGroupObject),

      service('cycles', models.Cycle),
      service('cycle_task_entries', models.CycleTaskEntry),
      service('cycle_task_groups', models.CycleTaskGroup),
      service('cycle_task_group_objects', models.CycleTaskGroupObject),
      service('cycle_task_group_object_tasks', models.CycleTaskGroupObjectTask)
      ]


def contributed_object_views():
  from . import models

  return [
      object_view(models.Workflow),
      object_view(models.Task),
      ]


from ggrc.services.common import Resource

@Resource.model_posted.connect_via(models.Cycle)
def handle_cycle_post(sender, obj=None, src=None, service=None):
  if not src.get('autogenerate'):
    return

  # Determine the relevant Workflow
  workflow = obj.workflow

  # Populate the top-level Cycle object
  obj.title = workflow.title
  obj.description = workflow.description

  # Populate CycleTaskGroups based on Workflow's TaskGroups
  for task_group in workflow.task_groups:
    cycle_task_group = models.CycleTaskGroup(
        cycle=obj,
        task_group=task_group,
        title=task_group.title,
        description=task_group.description,
        end_date=task_group.end_date,
        )
    #db.session.add(cycle_task_group)

    for task_group_object in task_group.task_group_objects:
      object = task_group_object.object

      cycle_task_group_object = models.CycleTaskGroupObject(
          cycle_task_group=cycle_task_group,
          task_group_object=task_group_object,
          title=object.title,
          )

      for task_group_task in task_group.task_group_tasks:
        task = task_group_task.task

        cycle_task_group_object_task = models.CycleTaskGroupObjectTask(
          cycle_task_group_object=cycle_task_group_object,
          task_group_task=task_group_task,
          title=task.title,
          description=task.description,
          sort_index=task_group_task.sort_index,
          end_date=task_group_task.end_date,
          contact=task_group.contact,
          status="Assigned",
          )
