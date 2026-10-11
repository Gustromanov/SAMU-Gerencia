"""Permissões baseadas em função (role)."""
from __future__ import annotations

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def _get_funcao(user) -> str | None:
    if not getattr(user, "is_authenticated", False):
        return None
    perfil = getattr(user, "perfil", None)
    return perfil.funcao if perfil else "ADMINISTRADOR"


def role_required(*funcoes: str):
    """Decorator para funções/views baseadas em classe (dispatch) ou function-based."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            funcao = _get_funcao(request.user)
            if funcao not in funcoes:
                return HttpResponseForbidden(
                    "Acesso negado. Esta área está disponível apenas para: "
                    + ", ".join(funcoes)
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


class RoleRequiredMixin:
    """Mixin para CBVs: define `allowed_roles = ['ADMINISTRADOR', ...]`."""

    allowed_roles: tuple[str, ...] = ("ADMINISTRADOR",)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        funcao = _get_funcao(request.user)
        if funcao not in self.allowed_roles:
            return HttpResponseForbidden(
                "Acesso negado. Esta área está disponível apenas para: "
                + ", ".join(self.allowed_roles)
            )
        return super().dispatch(request, *args, **kwargs)


def perfil_do(user):
    from .models import Perfil

    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.perfil
    except Perfil.DoesNotExist:
        return None
