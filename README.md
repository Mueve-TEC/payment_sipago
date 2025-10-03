# payment_sipago

Un módulo de pago para Odoo que permite integrar el proveedor de pagos **Sipago** al módulo de sitio web para tarjetas de débito y crédito.

## Descripción

Este módulo proporciona integración completa con la API de Sipago, permitiendo procesar pagos de la tienda web de Odoo mediante tarjetas de débito y crédito.

El módulo maneja automáticamente la autenticación OAuth2, la creación de órdenes de pago, webhooks para notificaciones de estado y el procesamiento de transacciones.

Este módulo fue desarrollado en el marco del programa SOL3 y de una beca de extensión de la Universidad Nacional de Córdoba.

## Características

- ✅ **Autenticación OAuth2**: Manejo automático de tokens JWT con renovación automática
- ✅ **Webhooks**: Procesamiento automático de notificaciones de estado
- ✅ **URLs de retorno**: Manejo de redirecciones de éxito y falla
- ✅ **Ambientes**: Soporte para desarrollo y producción
- ✅ **Validación**: Verificación de datos de transacciones
- ✅ **Logs detallados**: Para debugging y monitoreo

## Requisitos

- **Odoo**: Versión 16.0 o superior
- **Dependencias**: módulo `payment` de Odoo

## Instalación

1. **Clonar el repositorio**:

   ```bash
   git clone <url-del-repositorio>
   cd payment_sipago
   ```

2. **Copiar el módulo a tu instalación de Odoo**:

   ```bash
   cp -r payment_sipago /ruta/a/tu/odoo/addons/
   ```

3. **Actualizar la lista de módulos** en Odoo:
   - Ir a Aplicaciones → Actualizar lista de aplicaciones
   - Buscar "Payment Provider: Sipago"
   - Instalar el módulo

## Configuración

### 1. Credenciales de Sipago

Para obtener credenciales de desarrollo, consultar: <https://docs.sipago.coop/API%20Cobros/credencialDev>

### 2. Configuración en Odoo

1. **Ir a Ventas → Configuración → Proveedores de pago**
2. **Seleccionar el proveedor Sipago**
3. **Configurar los siguientes campos**:

| Campo | Descripción |
|-------|-------------|
| **Estado** | Activar el proveedor |
| **Ambiente Sipago** | Development/Production |
| **Client ID** | Credencial Client ID de Sipago |
| **Client Secret** | Credencial Client Secret de Sipago |

## Soporte

- **Documentación Sipago**: <https://docs.sipago.coop/>

## Licencia

AGPL-3

## Autores

- **Fundación Mueve**
