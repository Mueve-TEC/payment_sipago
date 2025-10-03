===========================
Payment Provider: Sipago
===========================

.. |badge1| image:: https://img.shields.io/badge/maturity-Production%2FStable-green.png
    :target: https://odoo-community.org/page/development-status
    :alt: Production/Stable
.. |badge2| image:: https://img.shields.io/badge/license-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-payment__sipago-lightgray.png?logo=github
    :target: https://github.com/Mueve-TEC/payment_sipago
    :alt: Mueve

|badge1| |badge2| |badge3|

Un módulo de pago para Odoo que permite integrar el proveedor de pagos **Sipago** al módulo de sitio web para tarjetas de débito y crédito.

Descripción
===========

Este módulo proporciona integración completa con la API de Sipago, permitiendo procesar pagos de la tienda web de Odoo mediante tarjetas de débito y crédito.

El módulo maneja automáticamente la autenticación OAuth2, la creación de órdenes de pago, webhooks para notificaciones de estado y el procesamiento de transacciones.

Este módulo fue desarrollado en el marco del programa SOL3 y de una beca de extensión de la Universidad Nacional de Córdoba.

Características
===============

- ✅ **Autenticación OAuth2**: Manejo automático de tokens JWT con renovación automática
- ✅ **Webhooks**: Procesamiento automático de notificaciones de estado
- ✅ **URLs de retorno**: Manejo de redirecciones de éxito y falla
- ✅ **Ambientes**: Soporte para desarrollo y producción
- ✅ **Validación**: Verificación de datos de transacciones
- ✅ **Logs detallados**: Para debugging y monitoreo

Requisitos
==========

- **Odoo**: Versión 16.0 o superior
- **Dependencias**: módulo `payment` de Odoo

Instalación
===========

Para instalar este módulo, debe seguir los siguientes pasos:

1. Clonar el repositorio:

   .. code-block:: bash

      git clone <url-del-repositorio>
      cd payment_sipago

2. Copiar el módulo a tu instalación de Odoo:

   .. code-block:: bash

      cp -r payment_sipago /ruta/a/tu/odoo/addons/

3. Actualizar la lista de módulos en Odoo:
   - Ir a **Aplicaciones** → **Actualizar lista de aplicaciones**
   - Buscar "Payment Provider: Sipago"
   - Haga clic en **Instalar**

Dependencias
============

Este módulo depende de los siguientes módulos de Odoo:

- `payment`

Configuración
=============

Credenciales de Sipago
----------------------

Para obtener credenciales de desarrollo, consultar: https://docs.sipago.coop/API%20Cobros/credencialDev

Configuración en Odoo
---------------------

1. Ir a **Ventas** → **Configuración** → **Proveedores de pago**
2. Seleccionar el proveedor **Sipago**
3. Configurar los siguientes campos:

+-------------------+------------------------------------------+
| Campo             | Descripción                              |
+===================+==========================================+
| **Estado**        | Activar el proveedor                     |
+-------------------+------------------------------------------+
| **Ambiente**      | Development/Production                   |
| **Sipago**        |                                          |
+-------------------+------------------------------------------+
| **Client ID**     | Credencial Client ID de Sipago           |
+-------------------+------------------------------------------+
| **Client Secret** | Credencial Client Secret de Sipago       |
+-------------------+------------------------------------------+

Uso
===

Una vez configurado el proveedor de pago Sipago:

1. Los clientes podrán seleccionar Sipago como método de pago en el checkout del sitio web
2. Serán redirigidos a la plataforma de Sipago para completar el pago
3. Las transacciones se actualizarán automáticamente mediante webhooks
4. Los pagos exitosos confirmarán automáticamente los pedidos

Soporte
=======

- **Documentación Sipago**: https://docs.sipago.coop/

Créditos
========

Autor
-----

Este módulo fue desarrollado por:

- **Fundación Mueve** (https://www.mueve.org.ar/)

Mantenedores
------------

Este módulo es mantenido por:

- **Fundación Mueve** (https://www.mueve.org.ar/)

Programa
--------

Este módulo fue desarrollado en el marco del programa **SOL3** y de una **beca de extensión de la Universidad Nacional de Córdoba**.