from django.db import models
from django.contrib.auth.models import User

class TokenUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    input_tokens = models.IntegerField()
    output_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.total_tokens} tokens"
