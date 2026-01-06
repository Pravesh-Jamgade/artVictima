#ifndef PTWV2_H
#define PTWV2_H

#include "page_table_walker_types.h"
#include "pagetable_walker.h"
#include "pagetable_buffer.h"
#include "cache_cntlr.h"
#include "subsecond_time.h"
#include "fixed_types.h"
#include "memory_manager.h"
#include <stdint.h>
#include "utopia_cache_template.h"
#include <vector>


namespace ParametricDramDirectoryMSI{

    class PageTableWalkerRadix: public PageTableWalker{

        public:

            struct{
                int number_of_levels;
                int *address_bit_indices;
                int *hit_percentages;
            } stats_radix;

            static int counter;
            UtopiaCache* shadow_cache;
            std::vector<IntPtr> addresses;
            Core* core;
            CacheCntlr *cache;
            String name;
            PageTableWalkerRadix(int number_of_levels,Core* _core,ShmemPerfModel* _m_shmem_perf_model,int *level_bit_indices,int *level_percentages, PWC* pwc, bool pwc_enabled,UtopiaCache* shadow_cache);
            ptw_table* starting_table;
            ShmemPerfModel* m_shmem_perf_model;
            SubsecondTime *latency_per_level;
            SubsecondTime init_walk(IntPtr eip, IntPtr address, UtopiaCache* shadow_cache, CacheCntlr *_cache,Core::lock_signal_t lock_signal,Byte* data_buf, UInt32 data_length,bool modeled, bool count) ;
            SubsecondTime InitializeWalkRecursive(IntPtr eip, IntPtr address,int level,ptw_table* new_table,Core::lock_signal_t lock_signal,Byte* data_buf, UInt32 data_length,bool modeled, bool count);
            int init_walk_functional(IntPtr address);
            int init_walk_recursive_functional(IntPtr address,int level,ptw_table* new_table);
            bool isPageFault(IntPtr address);
            bool isPageFaultHelper(uint64_t address,int level,ptw_table* new_table);
            std::vector<IntPtr> getAddresses(){return addresses;}
        private:
            std::vector<uint64_t> computeVpnIndices(uint64_t address);
            ptw_table* resolveTableForLevel(const std::vector<uint64_t> &vpn_indices, int target_level);
    };

}
#endif 