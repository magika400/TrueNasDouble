from middlewared.service import CRUDService


class VMService(CRUDService):

    async def __set_guest_vmemory(self, memory, overcommit):
        memory_available = await self.middleware.call('vm.get_available_memory', overcommit)
        memory_bytes = memory * 1024 * 1024
        if memory_bytes > memory_available:
            return False

        arc_max = sysctl.filter('vfs.zfs.arc.max')[0].value
        arc_min = sysctl.filter('vfs.zfs.arc.min')[0].value

        if arc_max > arc_min:
            new_arc_max = max(arc_min, arc_max - memory_bytes)
            self.logger.info(
                f'===> Setting ARC FROM: {arc_max} TO: {new_arc_max}'
            )
            sysctl.filter('vfs.zfs.arc.max')[0].value = new_arc_max
        return True

    @private
    async def init_guest_vmemory(self, vm, overcommit):
        guest_memory = vm.get('memory', None)
        guest_status = await self.middleware.call('vm.status', vm['id'])
        if guest_status.get('state') != 'RUNNING':
            setvmem = await self.__set_guest_vmemory(guest_memory, overcommit)
            if setvmem is False and not overcommit:
                raise CallError(f'Cannot guarantee memory for guest {vm["name"]}', errno.ENOMEM)
        else:
            raise CallError('bhyve process is running, we won\'t allocate memory')

    @private
    async def teardown_guest_vmemory(self, id):
        guest_status = await self.middleware.call('vm.status', id)
        if guest_status.get('state') != 'STOPPED':
            return

        vm = await self.middleware.call('datastore.query', 'vm.vm', [('id', '=', id)])
        guest_memory = vm[0].get('memory', 0) * 1024 * 1024
        arc_max = sysctl.filter('vfs.zfs.arc.max')[0].value
        arc_min = sysctl.filter('vfs.zfs.arc.min')[0].value
        new_arc_max = min(
            await self.middleware.call('vm.get_initial_arc_max'),
            arc_max + guest_memory
        )
        if arc_max != new_arc_max:
            if new_arc_max > arc_min:
                self.logger.debug(f'===> Give back guest memory to ARC: {new_arc_max}')
                sysctl.filter('vfs.zfs.arc.max')[0].value = new_arc_max
            else:
                self.logger.warn(
                    f'===> Not giving back memory to ARC because new arc_max ({new_arc_max}) <= arc_min ({arc_min})'
                )
