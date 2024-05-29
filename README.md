# gg-django-replace-migrations

This package offers a new django command: `replace_all_migrations`.
It can be use to get rid of old migrations as an alternative to django's `squashmigration` command.

## Reasoning

In big django projects, migration files easily pile up and get an increasing problem.
Django comes with the squashmigration command - however, it is hard to handle because of multiple reasons. Especially, it can not handle circular dependencies - they must be resolved [manually and with great care](https://stackoverflow.com/questions/37711402/circular-dependency-when-squashing-django-migrations).

One possible solution is to:

- Delete all existing migrations
- Run `./manage.py makemigrations`, so that it creates new initial migrations
- Run `./manage.py migrate --fake [new migrations]` or `./manage.py migrate --fake-initail` on all servers.

This workflow might work fine, if you have only few (production) servers - however, it becomes hard, when you have many environments with different versions of your application.

gg-django-replace-migrations also creates new initial migrations, but also, additionally, it adds the already existing migrations to the `replace` list of the new migration (That list is used by `squashmigrations` as well). By doing that, faking migrations is not needed anymore.

## Warning

The new replacing migrations will add not elidable special operations (`RunPython`, `RunSQL` or `SeparateDatabaseAndState`) at the end of the squash files. You will have to manually add them when suitable.

## Installation

Before you install, read the workflow below. You need to have the app installed in your project only on a specific branch temporarily.

Run

```
pip install gg-django-replace-migrations
```

and add `gg_django_replace_migrations` to your list of installed apps.

## Simple Workflow

If your apps are not depending on each other, you can use django-replace-migrations like this:

```
./manage.py replace_all_migrations --name replace [app1, app2, ...]
```

Note, that you will need to list all of your apps explicitly - otherwise django will also try to replace migrations from dependencies:

```
from django.apps import apps
print(" ".join(map(str, sorted({model._meta.app_label for model in apps.get_models()}))))
```

While `--name` could be omitted, it is highly recommended to use it so that you can easily recognize the new migrations.

If for any of your apps there are not one but two or more migrations created, your apps are depending on each other (see below).

You can leave your old migrations in the codebase. Old versions will continue to use the old migrations, while fresh installations will use the newly created replace migration instead.

If you remove the old migrations later, you will need to update the dependencies in your other migrations and replace all occurrences of the old migration with the new replace migration. You can easily do that with try-and-error (`migrate` will fail and tell you which dependency is missing)

## Workflow for depending apps

Due to the way django resolves the `replace` list, it can not handle circular dependencies within apps. To prevent an error during migration, you must delete the old migrations that you replaced.

If you have your application deployed on multiple servers, you must define down to which version, you will support upgrading and only replace those migrations.

Let’s assume that our current version of the application is 3.0 and we want to get rid of all migrations prior to 2.0.

The workflow for this would be:

- `git checkout 2.0`
- create a new branch `git checkout -b 2-0-delete-migrations`
- [delete all existing migrations in your apps](https://simpleisbetterthancomplex.com/tutorial/2016/07/26/how-to-reset-migrations.html)
- commit and note the commit hash
- `git checkout 2.0`
- create a new branch `git checkout -b 2-0-replace-migrations`
- Install `gg-django-replace-migration` here.
- run `./manage.py replace_all_migrations --name replace_2_0 app1, app2, ...` ([How to get all apps](https://stackoverflow.com/questions/4111244/get-a-list-of-all-installed-applications-in-django-and-their-attributes))
- commit and note the commit hash
- `git checkout [your main/feature branch]`
- `git cherry-pick [commit-hash from 2-0-delete-migrations]`
- `git cherry-pick [commit-hash from 2-0-replace-migrations]`
- Go over every migration in your app which was not replaced, and check the `dependencies` array. You need to make sure that every dependency listed was not replaced in the process, and the array is not out of date. If that's the case, then you need to specify the newest replaced migration instead. For example, in the app `A` there were two replace migrations created `0001_replace`, `0002_replace`. Migration `0026` is referencing migration `00015`, both from the app `A`, but `0015` was replaced. You need to swap `0015` with `0002_replace`.

Now you have all migrations prior to 2.0 removed and replaced with new migrations.

### Consequences

If your app is below 2.0 and you want to update to something after 2.0, you first need to update to 2.0

- upgrading from 1.0 to 1.5 will be possible
- upgrading from 2.0 to 3.0 will be possible
- upgrading from 1.0 to 3.0 will be **not** possible
