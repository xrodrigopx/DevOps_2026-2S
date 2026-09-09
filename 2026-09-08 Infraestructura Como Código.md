# Clase 2026-09-08: Infraestructura como Código (IaC)

## 1. ¿Qué es Infraestructura como Código?

**Infraestructura como Código (IaC)** es la práctica de aprovisionar, gestionar y configurar infraestructura (servidores, redes, bases de datos, etc.) describiéndola en archivos de configuración, en lugar de hacerlo a mano paso a paso sobre cada servidor o VM.

El cambio de enfoque es el siguiente:

- **Antes**: un administrador entra a cada servidor y ejecuta comandos manualmente para instalarlo, actualizarlo o configurarlo.
- **Con IaC**: ese mismo resultado se describe en un archivo (cuyo formato, sintaxis y estilo varían según la herramienta), y es la herramienta la que se encarga de aplicar esa configuración sobre la infraestructura real.

La ventaja no es solo el ahorro de tiempo: al quedar todo escrito en archivos, esa infraestructura se puede versionar, revisar y reproducir de forma consistente, algo imposible cuando la configuración vive únicamente en la memoria de quien la hizo a mano.

## 2. Breve historia: de la gestión manual a IaC

### 2.1 Antes de 1993: todo on-premise

Hasta 1990 no existía el concepto de *cloud*. Toda la infraestructura era **on-premise**: un administrador se encargaba de gestionar servidores físicos propios, con procesos manuales para cada configuración.

### 2.2 CFEngine (1993): el origen del enfoque declarativo

**CFEngine** es la primera herramienta que introduce el concepto de gestión de configuración: se instala en el servidor y permite describir el **estado deseado** del sistema en lugar de la secuencia de pasos para llegar a él. Esto es lo que se conoce como un enfoque **declarativo**: en vez de decir "instalá esto, después configurá aquello", se dice "quiero que el sistema termine así" y la herramienta se encarga de los pasos.

### 2.3 Puppet y Chef (2005–2009): DSLs propios

**Puppet** (2005) y **Chef** (2009) llevaron esa idea más allá, cada una con su propio **DSL** (*Domain Specific Language*, o lenguaje de dominio específico): un lenguaje pensado únicamente para describir el estado de un servidor, más simple y enfocado que un lenguaje de programación de propósito general como Python o Java.

### 2.4 Ansible (2012): agentless y YAML

**Ansible** aparece en 2012 y suma dos aportes clave:

- **Agentless**: a diferencia de Puppet o Chef, no requiere instalar ningún software en los servidores que se quieren gestionar (los *nodos gestionados*). Basta con tener Ansible instalado en un único servidor o VM (el *nodo de control*) y comunicarse con el resto vía **SSH**. Ya no existe el concepto de "cliente-servidor" de la herramienta.
- **YAML**: usa archivos YAML para definir instrucciones y configuración, un formato mucho más legible para humanos que un lenguaje de programación tradicional.

## 3. El problema de la rigidez

Estas herramientas de gestión de configuración resolvían cómo *configurar* un servidor, pero no resolvían cómo se *creaba* la infraestructura en sí. Ahí aparecía el problema de la **rigidez**:

- Las VMs se aprovisionaban y administraban de forma manual.
- La infraestructura se diseñaba para ser **mutable** (se modifica sobre el mismo servidor, ver sección 5).
- Todo era on-premise: la empresa tenía un rack físico con servidores propios corriendo todo internamente.
- Si se necesitaba más capacidad, había que adaptar el hardware físico existente (CPU, memoria, disco) al nuevo estado deseado — un proceso lento y limitado por lo que hubiera físicamente disponible.

## 4. El cambio de paradigma: AWS EC2

En 2006, Amazon lanza **EC2** (Elastic Compute Cloud), marcando un cambio de paradigma en cómo se aprovisiona infraestructura:

- Se **desacopla la capacidad de cómputo del hardware físico**.
- Permite pensar en capacidad (CPU, memoria, disco) como un recurso que se pide y se libera, sin preocuparse por la ubicación física de los racks.

A partir de este momento, el problema de la rigidez descrito en la sección 3 deja de ser tan determinante: si se necesita más capacidad, simplemente se aprovisiona más infraestructura en la nube, en lugar de depender del hardware físico disponible.

## 5. Infraestructura mutable vs. inmutable

### 5.1 Infraestructura mutable

En el modelo **mutable**, los cambios se aplican directamente sobre el servidor que ya está corriendo. Por ejemplo:

> Servidor web con Apache 2.4 → se modifica ese mismo servidor → ahora corre Nginx.

El **riesgo** de este enfoque es que si algo falla a mitad de camino, el servidor queda en un **estado intermedio**, no reproducible y difícil de diagnosticar (por ejemplo, con Apache parcialmente desinstalado y Nginx parcialmente instalado).

### 5.2 Infraestructura inmutable

En el modelo **inmutable**, en vez de modificar lo existente, se crea infraestructura completamente nueva con la versión deseada:

> Se crea la infraestructura nueva → si hay un error, se descarta y se reintenta → si no hay errores, recién ahí se redirige el tráfico a la nueva versión.

El tráfico solo se mueve una vez que la nueva versión fue validada. Nunca existe una versión a mitad de actualizar: o el servidor viejo sigue recibiendo tráfico, o lo recibe el nuevo, pero nunca un estado intermedio.

### 5.3 Consecuencia de la inmutabilidad: pérdida de datos

Si una aplicación guarda datos en la misma instancia que se destruye para reemplazarla, esos datos se pierden para siempre. La solución es **externalizar los datos**: sacarlos de la instancia y guardarlos en un lugar que sobreviva al reemplazo del servidor, como:

- Datos transaccionales en una base de datos gestionada aparte.
- Archivos u objetos en almacenamiento persistente (por ejemplo, un bucket de S3).

De esta forma, la instancia en sí queda **stateless** (sin estado): se la puede destruir y reemplazar sin perder información.

## 6. Las propiedades de IaC

### 6.1 Control de versiones

Al trabajar con archivos de configuración, la infraestructura se vuelve equiparable al código de una aplicación: se puede versionar con herramientas como **Git**, mantener un historial de cambios, revisarlos en un pull request y hacer rollback si algo sale mal.

### 6.2 Idempotencia

Una operación es **idempotente** cuando aplicarla una vez o aplicarla cien veces produce siempre el mismo resultado final. En la práctica, esto se logra porque la herramienta primero **verifica el estado actual** antes de actuar: si el paquete ya está instalado, no lo vuelve a instalar; si el servicio ya está corriendo, no hace nada. Por ejemplo, correr la misma configuración de Ansible diez veces seguidas deja el servidor exactamente en el mismo estado que correrla una sola vez.

### 6.3 Automatización y orquestación

La herramienta aplica los cambios en el orden correcto sobre múltiples recursos, sin necesidad de ejecutar pasos manuales uno por uno. Esto es especialmente importante cuando hay que gestionar muchas VMs o servidores al mismo tiempo: en vez de repetir el mismo proceso manual en cada uno, se define una única "hoja de ruta" y la herramienta la ejecuta en todos, sin intervención humana constante.

### 6.4 Inmutabilidad

Como se vio en la sección 5.2, en vez de modificar lo existente, se reemplaza por una versión nueva.

## 7. Enfoques de IaC: imperativo vs. declarativo

### 7.1 IaC imperativa (Ansible)

En el enfoque **imperativo** se especifican los pasos exactos a ejecutar, en el orden en que deben ejecutarse. Un playbook de Ansible es un buen ejemplo: describe una secuencia ordenada de tareas.

```yaml
---
- name: Configurar servidor web
  hosts: webservers
  become: true          # ejecutar las tareas con privilegios de administrador

  vars:
    paquete_web: nginx

  tasks:
    - name: Actualizar el índice de paquetes
      apt:
        update_cache: true

    - name: Instalar nginx
      apt:
        name: "{{ paquete_web }}"
        state: present

    - name: Asegurar que nginx esté corriendo y habilitado al inicio
      service:
        name: nginx
        state: started
        enabled: true
```

### 7.2 IaC declarativa (Terraform)

En el enfoque **declarativo** se declara el **estado deseado** y es la herramienta la que calcula qué pasos son necesarios para llegar a él. Terraform es el ejemplo típico:

```hcl
# Se declara el recurso deseado: una instancia EC2 con estas características.
# Terraform decide por sí mismo cómo crearla (llamadas a la API de AWS, orden, etc.)
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"

  tags = {
    Name = "servidor-web"
  }
}
```

## 8. Ansible

### 8.1 Qué es

**Ansible** es una herramienta de automatización de código abierto, mantenida por **Red Hat**. Es **agentless**: no necesita instalar ningún software en los servidores gestionados, sino que se conecta a ellos por **SSH** desde un único nodo de control. Se usa sobre todo para la **gestión de configuración** y el mantenimiento del día a día de servidores que **ya existen** (instalar paquetes, aplicar configuraciones, reiniciar servicios, etc.).

Esto la diferencia de Terraform (sección 9) en un punto clave: Ansible no está pensada, en primer lugar, para *crear* la infraestructura desde cero (eso es **provisioning**), sino para configurar la que ya está desplegada.

### 8.2 Principales utilidades

- **Automatización repetible**: las mismas tareas se pueden ejecutar una y otra vez con el mismo resultado (idempotencia, sección 6.2), sin depender de que alguien las repita manualmente igual cada vez.
- **Orquestación multi-servidor**: una misma ejecución puede aplicar cambios sobre decenas o cientos de servidores a la vez.
- **Infraestructura como código**: toda la configuración queda escrita en archivos versionables, en lugar de vivir solo en la cabeza de quien administra los servidores.

### 8.3 Conceptos básicos

- **Nodo de control**: la máquina donde está instalado Ansible y desde donde se ejecutan las tareas.
- **Nodo gestionado**: el servidor destino que se quiere configurar, al que Ansible se conecta por SSH.
- **Agentless**: no requiere instalar ningún software adicional en los nodos gestionados.
- **Inventario**: el archivo que lista los nodos gestionados y cómo agruparlos (ver sección 8.4).
- **Playbook**: un archivo YAML que define una o más *plays* a ejecutar.
- **Play**: dentro de un playbook, asocia un conjunto de tareas a un grupo de hosts determinado.
- **Tarea**: una acción concreta a ejecutar (instalar un paquete, copiar un archivo, reiniciar un servicio).
- **Módulo**: la unidad reutilizable que ejecuta el trabajo real de una tarea (por ejemplo, `apt`, `copy`, `service`).
- **Idempotencia**: ejecutar la misma tarea varias veces produce siempre el mismo resultado final (ver sección 6.2).

### 8.4 El inventario

El **inventario** es el archivo donde se listan los nodos gestionados, organizados por **grupos**. Todo host pertenece automáticamente al grupo especial `all`, y además se lo puede agrupar de forma más específica según su rol:

```ini
[webservers]
web1.midominio.com
web2.midominio.com

[databases]
db1.midominio.com

[webservers:vars]
ansible_user=ubuntu
```

Dentro del inventario también es posible asignar **variables** a un grupo o a un host particular (como `ansible_user` en el ejemplo). Ansible interpreta este archivo de forma similar a `/etc/hosts`: se pueden mapear IPs a los nombres de dominio definidos en el inventario, y luego referirse a esos nombres en los playbooks.

### 8.5 Comandos ad-hoc

Los **comandos ad-hoc** permiten ejecutar una tarea puntual directamente desde la terminal, sin necesidad de escribir un playbook completo. Son útiles para verificaciones rápidas o acciones únicas:

```bash
# Verificar conectividad con todos los hosts del inventario
ansible all -m ping

# Instalar nginx en el grupo "webservers", con privilegios de administrador
ansible webservers -m apt -a "name=nginx state=present" -b
```

### 8.6 Estructura de un playbook

Todo playbook comienza con `---` (marca de inicio de un documento YAML). A partir de ahí, cada *play* define el grupo de hosts al que aplica, sus variables y sus tareas:

```yaml
---
- name: Configurar servidor web        # nombre del play
  hosts: webservers                    # grupo del inventario al que aplica
  become: true

  vars:                                # variables del play
    paquete_web: nginx
    puerto: 80

  tasks:                               # sección de tareas
    - name: Instalar nginx
      apt:                             # módulo usado (apt)
        name: "{{ paquete_web }}"
        state: present

    - name: Copiar archivo de configuración
      copy:                            # otro módulo (copy)
        src: files/nginx.conf
        dest: /etc/nginx/nginx.conf
```

En resumen, el orden habitual dentro de un play es: **hosts** → **vars** → **tasks**, y cada tarea invoca un **módulo** (`apt`, `copy`, `service`, etc.) que hace el trabajo real.

### 8.7 Vaults

Ansible Vault es el mecanismo de seguridad para **almacenar información sensible** (contraseñas, API keys, certificados) de forma **cifrada con AES256** dentro del propio repositorio, en lugar de dejarla en texto plano.

```bash
# Crear un archivo cifrado nuevo
ansible-vault create secrets.yml

# Editar un archivo ya cifrado
ansible-vault edit secrets.yml

# Ejecutar un playbook que usa variables de un vault
ansible-playbook site.yml --ask-vault-pass
```

### 8.8 Acceso SSH a los nodos gestionados

Como Ansible es agentless, toda la comunicación con los nodos gestionados depende de tener **acceso SSH** configurado de antemano: la clave pública del nodo de control debe estar autorizada en cada nodo gestionado (por ejemplo, agregada a su `~/.ssh/authorized_keys`), y el usuario remoto debe tener los permisos necesarios (a menudo vía `sudo`, activado en los playbooks con la opción `become: true` usada en los ejemplos anteriores).

## 9. Terraform

### 9.1 Qué es

**Terraform** es una herramienta de IaC creada por **HashiCorp**, pensada para el **provisioning**: crear, modificar y destruir infraestructura completa (instancias, redes, bases de datos, DNS, etc.). A diferencia de Ansible, es **agnóstica al proveedor**: el mismo flujo de trabajo sirve para AWS, Azure, GCP u otros servicios, cambiando únicamente el *provider* que se use.

### 9.2 Flujo de trabajo

1. **Escribir**: se definen los recursos deseados en archivos `.tf`, escritos en **HCL** (*HashiCorp Configuration Language*) de forma declarativa.
2. **Planear** (`terraform plan`): Terraform calcula qué va a cambiar, comparando el estado deseado con el estado actual, y qué llamadas a la API del proveedor serán necesarias — sin aplicar todavía ningún cambio.
3. **Aplicar** (`terraform apply`): se ejecutan esos cambios en el orden correcto.

### 9.3 Arquitectura

El flujo real es el siguiente: el usuario escribe los archivos `.tf` → **Terraform Core** lee esa configuración y arma un grafo de dependencias entre recursos → usa los **providers** (plugins) para comunicarse con el servicio correspondiente (AWS, GCP, etc.) → antes de aprovisionar nada en la nube, guarda (o actualiza) el **state file** (`.tfstate`), que es el registro de lo que existe realmente.

- **Terraform Core**: el motor que interpreta los archivos `.tf`, arma el plan de ejecución y coordina a los providers.
- **Providers**: módulos/plugins que le permiten a Terraform comunicarse con un servicio en particular (un proveedor de nube, una base de datos, un servicio de DNS, etc.). Cada recurso que se declara pertenece a un provider específico.

### 9.4 Sintaxis básica

Los recursos se declaran con bloques `resource`, con la forma `resource "<tipo>" "<nombre_local>" { ... }`:

```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
}
```

El **nombre local** (`web`, en este caso) no es el nombre real del recurso en el proveedor: es un identificador interno que permite referenciar ese recurso en el resto del archivo, por ejemplo `aws_instance.web.id`.

### 9.5 Variables y outputs

Las **variables** permiten parametrizar la configuración (por ejemplo, el tipo de instancia o la región) en vez de dejar valores fijos ("hardcodeados") en el código:

```hcl
# variables.tf
variable "instance_type" {
  description = "Tipo de instancia EC2 a crear"
  type        = string
  default     = "t2.micro"
}
```

Los **outputs** exponen valores del estado resultante, útiles para mostrarlos en pantalla o pasarlos a otra configuración (por ejemplo, la IP pública de la instancia recién creada):

```hcl
# outputs.tf
output "instance_ip" {
  description = "IP pública de la instancia web"
  value       = aws_instance.web.public_ip
}
```

### 9.6 Comandos principales

El ciclo de vida de la infraestructura con Terraform se maneja con cuatro comandos básicos:

- **`terraform init`**: inicializa el directorio de trabajo, descarga los providers necesarios y configura el backend donde se guarda el state.
- **`terraform plan`**: muestra qué cambios se van a hacer, sin aplicarlos todavía (ver sección 9.2).
- **`terraform apply`**: aplica los cambios calculados en el plan, creando, modificando o eliminando recursos según corresponda.
- **`terraform destroy`**: elimina toda la infraestructura gestionada por esa configuración.

### 9.7 Terraform state

El **state** (`terraform.tfstate`) es el archivo donde Terraform guarda el mapeo entre lo declarado en el código y los recursos reales que existen en el proveedor. Es lo que le permite a Terraform saber, en cada `plan`, qué ya existe y qué falta crear, modificar o destruir — sin el state, Terraform no tendría forma de distinguir un recurso ya creado de uno nuevo. En proyectos de equipo, este archivo suele guardarse en un backend remoto (por ejemplo, un bucket de S3) en lugar de en el disco local, para que todos trabajen sobre el mismo estado.

### 9.8 Estructura de archivos de un proyecto

Un proyecto de Terraform bien organizado suele separar la configuración en varios archivos, cada uno con una responsabilidad clara:

- **`main.tf`**: los recursos principales de la infraestructura.
- **`variables.tf`**: la declaración de las variables de entrada (sin asignarles valores reales ahí).
- **`outputs.tf`**: los valores de salida que se quieren exponer una vez aplicada la configuración.
- **`providers.tf`**: la configuración de los providers utilizados (proveedor de nube, versión, región, credenciales).

Buenas prácticas para mantener un proyecto escalable:

- Separar variables y outputs del resto del código, en lugar de mezclar todo en `main.tf`.
- No hardcodear valores sensibles (credenciales, IPs); usar variables y archivos `.tfvars` que no se suban al repositorio.
- Fijar (*pin*) la versión de los providers, para evitar cambios inesperados de comportamiento.
- Usar un backend remoto para el state file cuando se trabaja en equipo.
- Dividir la infraestructura en **módulos** reutilizables a medida que el proyecto crece, en vez de un único archivo gigante.

## 10. Ansible vs. Terraform

| Aspecto | Ansible | Terraform |
|---|---|---|
| Propósito principal | Configuration management: configurar y mantener servidores que ya existen | Provisioning: crear, modificar y destruir infraestructura desde cero |
| Paradigma | Imperativo (secuencia ordenada de tareas) | Declarativo (se declara el estado deseado) |
| Estado | No mantiene un registro propio; aplica sobre el estado real actual en cada corrida | Mantiene un state file (`.tfstate`) que registra lo que existe |
| Comunicación | Agentless, vía SSH a cada nodo | Vía providers/plugins que llaman a la API del proveedor |
| Alcance típico | Instalar paquetes, aplicar configuraciones, tareas de día a día | Crear VMs, redes, bases de datos y demás recursos de infraestructura |

En la práctica, ambas herramientas se suelen usar juntas: Terraform aprovisiona la infraestructura base, y Ansible se encarga de configurarla una vez que existe.

## 11. Resumen

1. **IaC** reemplaza la configuración manual de infraestructura por archivos de configuración versionables.
2. La evolución fue: CFEngine (1993, declarativo) → Puppet/Chef (2005-2009, DSLs propios) → Ansible (2012, agentless + YAML).
3. El problema de la **rigidez** (infraestructura on-premise, mutable) se redujo con la llegada de AWS EC2 (2006), que desacopló el cómputo del hardware físico.
4. La **infraestructura inmutable** (reemplazar en vez de modificar) evita estados intermedios corruptos, a costa de requerir **externalizar los datos** para no perderlos al destruir una instancia.
5. Las cuatro propiedades clave de IaC son: control de versiones, idempotencia, automatización/orquestación e inmutabilidad.
6. Hay dos enfoques de IaC: **imperativo** (Ansible, se especifican los pasos) y **declarativo** (Terraform, se especifica el estado deseado).
7. **Ansible** es agentless, se conecta por SSH, y se usa para configuration management: inventario, playbooks, plays, tasks y módulos son sus piezas básicas; Vault protege datos sensibles con AES256.
8. **Terraform** es agnóstico al proveedor y se usa para provisioning: su flujo es escribir → planear → aplicar, apoyado en Terraform Core, providers y el state file.
9. Ansible y Terraform no compiten tanto como se complementan: Terraform crea la infraestructura, Ansible la configura.
