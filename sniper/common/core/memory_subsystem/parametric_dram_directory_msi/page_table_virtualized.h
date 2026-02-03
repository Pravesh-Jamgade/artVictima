//create class that inherits from page table walker
#include "pagetable_walker_radix.h"
#include "pagetable_walker.h"
#include "tlb.h"
#include "hit_where.h"
#include <vector>
#include <array>
#include <inttypes.h>

namespace ParametricDramDirectoryMSI
{
   class PageTableVirtualized : public PageTableWalker
   {

   private:
         PageTableWalkerRadix *ptw_radix_host;
         PageTableWalkerRadix *ptw_radix_guest;
         int num_levels;
         TLB* nested_tlb;
         ComponentLatency m_nested_tlb_access_latency;

         ComponentLatency m_tlb_l1_cache_access;
         ComponentLatency m_tlb_l2_cache_access; 
         ComponentLatency m_tlb_nuca_cache_access;
         std::vector<UInt64> guest_nested_hits;
         std::vector<UInt64> guest_nested_misses;
         std::vector<UInt64> guest_host_ptw_initiates;
         std::vector<UInt64> host_psc_hits;
         std::vector<UInt64> host_psc_misses;
         std::vector<std::array<UInt64, HitWhere::NUM_HITWHERES>> host_hitwhere;
   
   public:

      PageTableVirtualized(int number_of_levels,
                           Core* _core, 
                           ShmemPerfModel* _m_shmem_perf_model, 
                           int *level_bit_indices,
                           int *level_percentages, 
                           PWC* pwc, 
                           bool pwc_enabled,
                           UtopiaCache* _shadow_cache);
      


      ~PageTableVirtualized(){
         String csv_output_path = Sim()->getConfig()->formatOutputFileName(
            ("proposed_virtualized_core" + std::to_string(core_id) + ".csv").c_str());
         FILE *csv_fp = fopen(csv_output_path.c_str(), "a");
         if(csv_fp){
            for (int level = 0; level < num_levels; ++level){
               int lvl = level + 1;
               fprintf(csv_fp, "proposed_nested_tlb_L%d_hits,%" PRIu64 "\n", lvl, guest_nested_hits[level]);
               fprintf(csv_fp, "proposed_nested_tlb_L%d_misses,%" PRIu64 "\n", lvl, guest_nested_misses[level]);
               fprintf(csv_fp, "proposed_nested_tlb_L%d_host_ptw_initiates,%" PRIu64 "\n", lvl, guest_host_ptw_initiates[level]);
            }
            for (int level = 0; level < num_levels; ++level){
               int lvl = level + 1;
               fprintf(csv_fp, "proposed_host_ptw_L%d_psc_hits,%" PRIu64 "\n", lvl, host_psc_hits[level]);
               fprintf(csv_fp, "proposed_host_ptw_L%d_psc_misses,%" PRIu64 "\n", lvl, host_psc_misses[level]);
               fprintf(csv_fp, "proposed_host_ptw_L%d_hitwhere", lvl);
               for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where){
                  fprintf(csv_fp, ",%s", HitWhereString(static_cast<HitWhere::where_t>(where)));
               }
               fprintf(csv_fp, "\n");
               fprintf(csv_fp, "proposed_host_ptw_L%d_hitwhere", lvl);
               for (int where = 0; where < HitWhere::NUM_HITWHERES; ++where){
                  fprintf(csv_fp, ",%" PRIu64, host_hitwhere[level][where]);
               }
               fprintf(csv_fp, "\n");
            }
            fclose(csv_fp);
         }
         delete ptw_radix_guest;
         delete ptw_radix_host;
      }


      SubsecondTime init_walk(IntPtr eip, IntPtr address,
         UtopiaCache* shadow_cache,
         CacheCntlr *_cache,
         Core::lock_signal_t lock_signal,
         Byte* data_buf, UInt32 data_length,
         bool modeled, bool count);

      int init_walk_functional(IntPtr address);
      bool isPageFault(IntPtr address);
      void setMemoryManager(ParametricDramDirectoryMSI::MemoryManager* _memory_manager) override {
         ptw_radix_guest->setMemoryManager(_memory_manager);
         ptw_radix_host->setMemoryManager(_memory_manager);
      }
      void setPageTableBuffer(PageTableBuffer* buffer) {
         PageTableWalker::setPageTableBuffer(buffer);
         ptw_radix_guest->setPageTableBuffer(buffer);
         ptw_radix_host->setPageTableBuffer(buffer);
      }
   };

};
