from django.test import TestCase
from .models import Task

class TaskModelTest(TestCase):
    def test_create_task(self):
        task = Task.objects.create(title="Learn Django on SkilTrix")
        self.assertEqual(task.title, "Learn Django on SkilTrix")
        self.assertFalse(task.completed)
